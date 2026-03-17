"""
core/stages/extraction.py
Stage 5 — Extração de CSS, imagens e scripts externos
"""
import os
import re
import hashlib
import logging
from typing import Dict, Any, Optional

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
        os.makedirs(paths['SCRIPTS_DIR'], exist_ok=True)

        # CSS externo
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if not href:
                continue
            full_url = _resolve_url(href, base_url)
            if full_url:
                filename = f"style_{hashlib.md5(full_url.encode()).hexdigest()[:8]}.css"
                local    = os.path.join(paths['STYLES_DIR'], filename)
                if _download_asset(full_url, local):
                    link['href'] = f"styles/{filename}"

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
        context['css']  = _extract_style_tags(soup)
        context['css']  = _extract_css_base64_images(context['css'], paths['IMAGES_DIR'])
        context['soup'] = _extract_images(soup, base_url, paths['IMAGES_DIR'])
        return context


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _resolve_url(url: str, base_url: Optional[str]) -> Optional[str]:
    if url.startswith('http'):
        return url
    if base_url:
        return f"{base_url.rstrip('/')}/{url.lstrip('/')}"
    return None


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
    pattern = re.compile(r'url\((data:image/[\w+]+;base64,[^)]+)\)')

    def repl(match):
        data_url = match.group(1)
        m = re.match(r'data:image/(\w+);base64,(.+)', data_url)
        if not m:
            return match.group(0)
        ext, b64 = m.groups()
        name = f"css_img_{hashlib.md5(b64.encode()).hexdigest()[:12]}.{ext}"
        path = os.path.join(images_dir, name)
        if not os.path.exists(path):
            data = safe_b64decode(b64)
            if data:
                save_file(path, data, is_bytes=True)
        return f'url("../images/{name}")'

    return pattern.sub(repl, css)


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

    logger.info(f"Imagens processadas: {count}")
    return soup
