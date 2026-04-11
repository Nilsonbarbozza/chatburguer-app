"""
core/stages/cleaning.py
Stage 3 — Limpeza de HTML, semântica ARIA e limpeza do <head>
"""
import logging
from typing import Dict, Any

from bs4 import BeautifulSoup, Comment
from core.pipeline import ProcessorStage
from core.utils    import setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class CleaningStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 3: Limpeza e Semântica ===")
        soup = context['soup']
        soup = _clean_html(soup)
        soup = _semantic_conversion(soup)
        soup = _clean_head(soup)
        soup = _clean_video_semantics(soup)
        context['soup'] = soup
        return context


def _clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if not any(m in str(c) for m in ['HEADER', 'MAIN', 'FOOTER', 'SECTION']):
            c.extract()
    logger.info("HTML limpo")
    return soup


def _semantic_conversion(soup: BeautifulSoup) -> BeautifulSoup:
    """Aplica roles ARIA genéricos baseados em padrões de classe/id."""
    conversions = 0
    role_patterns = [
        (['header', 'masthead', 'site-header', 'page-header'],    'banner'),
        (['footer', 'site-footer', 'page-footer', 'bottom'],      'contentinfo'),
        (['nav', 'navbar', 'menu', 'navigation', 'breadcrumb'],   'navigation'),
        (['main', 'main-content', 'primary', 'content-area'],     'main'),
        (['sidebar', 'aside', 'secondary'],                       'complementary'),
        (['search', 'search-box', 'search-form'],                 'search'),
        (['hero', 'banner', 'jumbotron'],                         'region'),
    ]
    for div in soup.find_all('div'):
        classes  = ' '.join(div.get('class', [])).lower()
        div_id   = (div.get('id') or '').lower()
        if div.get('role'):
            continue
        for patterns, role in role_patterns:
            if any(p in classes or p in div_id for p in patterns):
                div['role'] = role
                conversions += 1
                break
    logger.info(f"Semântica ARIA: {conversions} elementos")
    return soup


def _clean_head(soup: BeautifulSoup) -> BeautifulSoup:
    if not soup.head:
        return soup

    remove_rels = ['dns-prefetch', 'preconnect', 'modulepreload', 'apple-touch-icon', 'mask-icon']
    for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in remove_rels)):
        link.decompose()

    for meta in soup.find_all('meta'):
        name       = (meta.get('name') or '').lower()
        prop       = (meta.get('property') or '').lower()
        http_equiv = (meta.get('http-equiv') or '').lower()
        if 'content-security-policy' in http_equiv or 'origin-trial' in http_equiv:
            meta.decompose(); continue
        if name.startswith('msapplication-') or name in ('theme-color', 'keywords'):
            meta.decompose(); continue
        if prop.startswith('og:') or name.startswith('twitter:'):
            meta.decompose(); continue
        if meta.has_attr('data-react-helmet'):
            meta.decompose(); continue

    for script in soup.find_all('script'):
        src     = script.get('src', '')
        content = (script.string or '').lower()
        if any(x in src for x in ['googletagmanager', 'gtm.js', 'analytics', 'facebook.net', 'tiktok', 'clarity']) \
                or 'gtag' in content:
            script.decompose()

    for ld in soup.find_all('script', type='application/ld+json'):
        ld.decompose()

    logger.info("Head limpo")
    return soup


def _clean_video_semantics(soup: BeautifulSoup) -> BeautifulSoup:
    """Melhora a semântica de tags de vídeo e organiza fallbacks."""
    videos = soup.find_all('video')
    for video in videos:
        # 1. Limpa atributos booleanos
        for attr in ['autoplay', 'loop', 'muted', 'playsinline', 'webkit-playsinline']:
            if video.has_attr(attr):
                # Usar string vazia ou herdar o valor original se for boolean
                video[attr] = '' # Em HTML5 isso resulta em apenas 'attr' se for void

        # 2. Tenta capturar fallback (link/imagem logo após o vídeo que aponta para o mesmo recurso)
        nxt = video.find_next_sibling()
        moved_link = None
        if nxt and nxt.name == 'a':
            href = nxt.get('href', '')
            if href.endswith('.mp4') or href.endswith('.webm'):
                logger.debug("Movendo fallback de vídeo (link) para dentro da tag <video>")
                moved_link = nxt.extract()
                video.append(moved_link)
        elif nxt and nxt.name == 'img':
            video.append(nxt.extract())

        # 3. Inteligência Adicional: Se source estiver vazia, tenta usar o href do link movido
        for source in video.find_all('source'):
            if not source.get('src') and not source.get('data-src') and moved_link:
                href = moved_link.get('href')
                if href:
                    logger.info(f"Herdando src do link de fallback: {href}")
                    source['src'] = href

    if videos:
        logger.info(f"Semântica de vídeo processada: {len(videos)} tags")
    return soup
