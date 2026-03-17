"""
core/stages/optimization.py
Stage 7 + Stage 10 — Otimização CSS (LightningCSS / fallback regex + PostCSS pipeline)
"""
import os
import re
import tempfile
import logging
from typing import Dict, Any

from core.pipeline import ProcessorStage
from core.config   import CONFIG, get_paths
from core.utils    import tool_available, run_command, setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class OptimizationStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 7: Otimização CSS ===")
        paths = get_paths()

        if CONFIG['USE_LIGHTNINGCSS']:
            context['css'] = _optimize_lightningcss(context['css'])
        else:
            context['css'] = _optimize_regex(context['css'])

        # Garante que o <head> aponta para styles/styles.css
        if context['css'] and context['soup'].head:
            head = context['soup'].head
            if not head.find('link', href='styles/styles.css'):
                link = context['soup'].new_tag('link', rel='stylesheet', href='styles/styles.css')
                head.append(link)

        return context


class PostCssOptimizationStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 10: Otimização Final CSS ===")
        paths    = get_paths()
        out      = context.get('output', {})
        html_f   = out.get('html_file')
        css_f    = out.get('css_file')

        if not (html_f and css_f and os.path.exists(html_f) and os.path.exists(css_f)):
            return context

        if tool_available(CONFIG['PURGECSS_BIN']) and CONFIG['USE_PURGECSS']:
            logger.info("  PurgeCSS: removendo classes não utilizadas...")
            out_dir = os.path.dirname(css_f)
            run_command([CONFIG['PURGECSS_BIN'], '--css', css_f, '--content', html_f, '-o', out_dir])

        if tool_available(CONFIG['LIGHTNINGCSS_BIN']) and CONFIG['USE_LIGHTNINGCSS']:
            logger.info("  LightningCSS: minificando CSS final...")
            run_command([
                CONFIG['LIGHTNINGCSS_BIN'], css_f,
                '--targets', CONFIG['LIGHTNINGCSS_TARGETS'],
                '-o', css_f, '--minify',
            ])

        if tool_available(CONFIG['PRETTIER_BIN']) and CONFIG['USE_PRETTIER']:
            logger.info("  Prettier: formatando CSS...")
            run_command([CONFIG['PRETTIER_BIN'], '--write', css_f])

        return context


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _sanitize_css(css: str) -> str:
    if not css:
        return ''
    corrupt = [r'webpacity', r"no'h", r'fraansform', r'4tate3d', r'origing\)', r'border:0cus-inner']
    for p in corrupt:
        css = re.sub(p, '', css, flags=re.IGNORECASE)
    css = re.sub(r';\s*;', ';', css)
    opens  = css.count('{')
    closes = css.count('}')
    if opens > closes:
        css += '}' * (opens - closes)
    return css


def _optimize_lightningcss(css_text: str) -> str:
    binary = CONFIG['LIGHTNINGCSS_BIN']
    if not css_text.strip():
        return ''
    if not tool_available(binary):
        logger.warning("lightningcss não encontrado — fallback regex")
        return _optimize_regex(css_text)

    css_text = _sanitize_css(css_text)
    with tempfile.NamedTemporaryFile(suffix='.css', mode='w', delete=False, encoding='utf-8') as tmp:
        tmp.write(css_text)
        tmp_path = tmp.name

    try:
        cmd = [binary, tmp_path, '--targets', CONFIG['LIGHTNINGCSS_TARGETS']]
        if CONFIG['MINIFY_CSS']:
            cmd.append('--minify')
        result = run_command(cmd)
        if result is not None:
            logger.info("CSS processado pelo LightningCSS")
            return result
        logger.warning("LightningCSS falhou — fallback regex")
        return _optimize_regex(css_text)
    finally:
        os.unlink(tmp_path)


def _optimize_regex(css_text: str) -> str:
    minified = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    minified = re.sub(r'\s+', ' ', minified)
    minified = re.sub(r'\s*([{};:,>~+])\s*', r'\1', minified)
    return minified.strip()
