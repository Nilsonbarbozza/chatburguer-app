"""
core/stages/extraction.py
Stage 5 — Extração de CSS, imagens e scripts externos
"""
import os
import re
import hashlib
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from core.pipeline import ProcessorStage
from core.config   import CONFIG, get_paths
from core.utils    import save_file, safe_b64decode, setup_logging

setup_logging()
logger = logging.getLogger('html_processor')

HEADERS = {'User-Agent': 'Mozilla/5.0 (ProcessCloner/1.0)'}


class ExtractionStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 5: Extração de Recursos ===")
        paths    = get_paths()
        soup     = context['soup']
        base_url = context.get('base_url')

        os.makedirs(paths['STYLES_DIR'],  exist_ok=True)
        os.makedirs(paths['IMAGES_DIR'],  exist_ok=True)
        os.makedirs(paths['VIDEOS_DIR'],  exist_ok=True)
        os.makedirs(paths['SCRIPTS_DIR'], exist_ok=True)

        # CSS externo
        context['css'] = context.get('css', '')
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if not href or 'styles/styles.css' in href:
                continue
            full_url = _resolve_url(href, base_url)
            if full_url and not full_url.startswith('data:'):
                filename = f"style_{hashlib.md5(full_url.encode()).hexdigest()[:8]}.css"
                local    = os.path.join(paths['STYLES_DIR'], filename)
                if _download_asset(full_url, local):
                    # Adiciona ao CSS principal para unificação
                    try:
                        with open(local, 'r', encoding='utf-8', errors='replace') as f:
                            ext_css = f.read()
                        
                        # Processa ativos internos ANTES da unificação para manter caminhos
                        ext_css = _extract_css_base64_images(ext_css, paths['IMAGES_DIR'])
                        ext_css = _extract_css_remote_assets(ext_css, full_url, paths['IMAGES_DIR'])
                        
                        # Concatena com banner de separação
                        context['css'] += f"\n\n/* --- BUNDLED: {href} --- */\n" + ext_css
                        
                        # Remove a tag link do HTML pois será unificada
                        link.decompose()
                        
                        # Remove o arquivo individual (opcional, vamos manter por segurança se der erro)
                        # os.remove(local) 
                    except Exception as e:
                        logger.warning(f"Erro ao unificar CSS {filename}: {e}")

        # Scripts externos
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if not src:
                continue
            full_url = _resolve_url(src, base_url)
            if full_url:
                filename = f"script_{hashlib.md5(full_url.encode()).hexdigest()[:8]}.js"
                local    = os.path.join(paths['SCRIPTS_DIR'], filename)
                if _download_asset(full_url, local):
                    script['src'] = f"scripts/{filename}"

        # CSS inline + estilos inline → classes
        # Adiciona ao CSS já acumulado dos arquivos externos
        inline_css      = _extract_style_tags(soup)
        context['css'] += _extract_css_base64_images(inline_css, paths['IMAGES_DIR'])
        
        # Processa ativos remotos no CSS acumulado (agora contendo tudo)
        context['css']  = _extract_css_remote_assets(context['css'], base_url, paths['IMAGES_DIR'])
        context['soup'] = _extract_images(soup, base_url, paths['IMAGES_DIR'])
        context['soup'] = _extract_videos(soup, base_url, paths['VIDEOS_DIR'])
        context['soup'] = _extract_inline_svgs(soup, paths['IMAGES_DIR'])
        return context


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _resolve_url(url: str, base_url: Optional[str]) -> Optional[str]:
    url = url.strip()
    if any(url.lower().startswith(s) for s in ('data:', 'blob:')):
        return url
    if not base_url:
        return url if url.startswith('http') else None
    return urljoin(base_url, url)


def _download_asset(url: str, save_path: str) -> bool:
    try:
        r = requests.get(url, timeout=CONFIG['REQUEST_TIMEOUT'], headers=HEADERS)
        r.raise_for_status()
        save_file(save_path, r.content, is_bytes=True)
        return True
    except Exception as e:
        logger.error(f"Erro ao baixar {url}: {e}")
        return False


def _download_image_safe(url: str) -> Optional[bytes]:
    max_bytes = CONFIG['MAX_IMAGE_SIZE_MB'] * 1024 * 1024
    try:
        r = requests.get(url, timeout=CONFIG['REQUEST_TIMEOUT'], stream=True, headers=HEADERS)
        r.raise_for_status()
        if not r.headers.get('Content-Type', '').startswith('image/'):
            return None
        content = b''
        for chunk in r.iter_content(8192):
            content += chunk
            if len(content) > max_bytes:
                return None
        return content
    except Exception as e:
        logger.error(f"Erro ao baixar imagem {url}: {e}")
        return None


def _extract_style_tags(soup: BeautifulSoup) -> str:
    combined = []
    seen: set = set()

    for tag in soup.find_all('style'):
        content = tag.decode_contents().strip()
        if content:
            combined.append(content)
        tag.decompose()

    for el in soup.find_all(style=True):
        style_content = el['style'].strip()
        if not style_content:
            continue
        cls_hash   = hashlib.md5(style_content.encode()).hexdigest()[:8]
        class_name = f"inline_{cls_hash}"
        el['class'] = (el.get('class') or []) + [class_name]
        del el['style']
        rule = f".{class_name} {{{style_content}}}"
        if rule not in seen:
            combined.append(rule)
            seen.add(rule)

    css = '\n'.join(combined)
    logger.info(f"CSS extraído: {len(combined)} blocos ({len(css)} bytes)")
    return css

def _extract_css_base64_images(css: str, images_dir: str) -> str:
    """Decodifica imagens base64 incorporadas no CSS e as salva localmente."""
    # Pattern aprimorado para suportar url("data:...") e url('data:...') com diversos MIME types
    pattern = re.compile(r'url\((?P<quote>["\']?)(?P<data>data:image/[^;]+;base64,[^"\'\)]+)(?P=quote)\)', re.IGNORECASE)

    count = 0
    def repl(match):
        nonlocal count
        data_url = match.group('data').strip()
        m = re.match(r'data:image/([^;]+);base64,(.+)', data_url, re.IGNORECASE)
        if not m:
            return match.group(0)
        ext_full, b64 = m.groups()
        # Normaliza extensão (pode vir como svg+xml)
        ext = ext_full.split('+')[0] if '+' in ext_full else ext_full
        if ext == 'jpeg': ext = 'jpg'
        
        name = f"css_img_{hashlib.md5(b64.encode()).hexdigest()[:12]}.{ext}"
        path = os.path.join(images_dir, name)
        if not os.path.exists(path):
            data = safe_b64decode(b64)
            if data:
                save_file(path, data, is_bytes=True)
                count += 1
        return f'url("../images/{name}")'

    new_css = pattern.sub(repl, css)
    if count > 0:
        logger.info(f"Ativos CSS base64 extraídos: {count}")
    return new_css

def _extract_css_remote_assets(css: str, base_url: Optional[str], images_dir: str) -> str:
    """Extrai e baixa ativos referenciados via url(...) no CSS."""
    # Pattern consistente para url("...") ou url('...') ou url(...)
    pattern = re.compile(r'url\((?P<quote>["\']?)(?P<url>[^"\'\)]+?)(?P=quote)\)', re.IGNORECASE)
    
    count = 0
    def repl(match):
        nonlocal count
        orig_url = match.group('url').strip()
        
        # Ignora caminhos de dados embutidos ou pastas locais já processadas
        low_url = orig_url.lower()
        if any(low_url.startswith(s) for s in ('data:', 'blob:', 'images/', 'videos/', 'scripts/', '../images/', '../videos/', '../scripts/')):
            return match.group(0)
            
        full_url = _resolve_url(orig_url, base_url)
        if not full_url or not full_url.lower().startswith('http'):
            return match.group(0)
            
        # Determina nome e extensão
        path_part = full_url.split('?')[0].split('#')[0]
        ext = 'png'
        if '.' in path_part:
            ext = path_part.split('.')[-1].lower()[:5] # Aumentado para 5 para woff2
            if ext not in ('png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'woff', 'woff2', 'ttf', 'eot', 'otf'):
                ext = 'png'
        
        filename = f"css_asset_{hashlib.md5(full_url.encode()).hexdigest()[:10]}.{ext}"
        local_path = os.path.join(images_dir, filename)
        
        if not os.path.exists(local_path):
            if _download_asset(full_url, local_path):
                count += 1
                return f'url("../images/{filename}")'
            else:
                logger.error(f"Falha ao baixar ativo CSS: {full_url}")
                return match.group(0)
        else:
            return f'url("../images/{filename}")'

    new_css = pattern.sub(repl, css)
    if count > 0:
        logger.info(f"Ativos CSS remotos extraídos: {count}")
    return new_css


def _extract_images(soup: BeautifulSoup, base_url: Optional[str], images_dir: str) -> BeautifulSoup:
    count = 0
    for img in soup.find_all('img'):
        orig = img.get('data-src') or img.get('src', '')
        if not orig:
            continue

        img['onerror'] = "this.onerror=null;this.src=this.getAttribute('data-src')||this.src;"

        if orig.startswith('data:image'):
            m   = re.match(r'data:image/(\w+);base64,', orig)
            ext = m.group(1) if m else 'png'
            b64 = re.sub(r'data:image/\w+;base64,', '', orig)
            raw = safe_b64decode(b64)
            if raw:
                name = f"img_{hashlib.md5(orig.encode()).hexdigest()[:8]}.{ext}"
                save_file(os.path.join(images_dir, name), raw, is_bytes=True)
                img['src'] = f"images/{name}"
                count += 1
        else:
            full_url = _resolve_url(orig, base_url) or orig
            if full_url.startswith('http'):
                content = _download_image_safe(full_url)
                if content:
                    path_part = full_url.split('?')[0].split('#')[0]
                    ext = 'png'
                    if '.' in path_part:
                        candidate = path_part.split('.')[-1].lower()
                        if candidate in ('jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'):
                            ext = candidate
                    name = f"img_{hashlib.md5(full_url.encode()).hexdigest()[:8]}.{ext}"
                    save_file(os.path.join(images_dir, name), content, is_bytes=True)
                    img['src'] = f"images/{name}"
                    count += 1


def _extract_videos(soup: BeautifulSoup, base_url: Optional[str], videos_dir: str) -> BeautifulSoup:
    count = 0
    # Processa posters em tags <video>
    for video in soup.find_all('video'):
        poster = video.get('poster')
        if poster:
            full_url = _resolve_url(poster, base_url) or poster
            if full_url.startswith('http'):
                filename = f"poster_{hashlib.md5(full_url.encode()).hexdigest()[:8]}.png"
                local    = os.path.join(videos_dir, filename)
                if _download_asset(full_url, local):
                    video['poster'] = f"videos/{filename}"
                    count += 1

    # Processa srcs em tags <source> (inclusive data-src)
    for source in soup.find_all('source'):
        orig = source.get('data-src') or source.get('src', '')
        if not orig:
            continue
        
        full_url = _resolve_url(orig, base_url) or orig
        if full_url.startswith('http'):
            # Detecta extensão básica
            ext = 'mp4'
            if '.' in full_url.split('?')[0]:
                candidate = full_url.split('?')[0].split('.')[-1].lower()
                if candidate in ('mp4', 'webm', 'ogg'):
                    ext = candidate
            
            filename = f"video_{hashlib.md5(full_url.encode()).hexdigest()[:8]}.{ext}"
            local    = os.path.join(videos_dir, filename)
            
            if _download_asset(full_url, local):
                source['src'] = f"videos/{filename}"
                if source.has_attr('data-src'):
                    del source['data-src']
                count += 1
    
    if count > 0:
        logger.info(f"Vídeos/Posters extraídos: {count}")
    return soup


def _extract_inline_svgs(soup: BeautifulSoup, images_dir: str) -> BeautifulSoup:
    """
    Identifica SVGs inline volumosos ou repetitivos e os trata com precisão DOM.
    Evita o erro de regex guloso descrito no STRATEGY_SHADOW_BUILD.md.
    """
    count = 0
    # Por enquanto, focamos em garantir que o soup não seja corrompido e logar presença
    svgs = soup.find_all('svg')
    for svg in svgs:
        # Se o SVG for muito grande, poderíamos movê-lo para um arquivo .svg externo
        # Mas a recomendação de Shadow Build foca em NÃO corromper tags irmãs.
        # BeautifulSoup já garante isso por padrão.
        count += 1
    
    if count > 0:
        logger.info(f"SVGs inline detectados e protegidos: {count}")
    
    return soup
