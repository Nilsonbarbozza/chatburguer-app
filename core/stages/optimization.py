"""
core/stages/optimization.py
Stage 7 + Stage 10 — Otimização CSS (LightningCSS / fallback regex + PostCSS Shadow Build)
"""
import os
import re
import shutil
import tempfile
import logging
from glob import glob
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
        logger.info("=== ETAPA 10: Shadow Build + Otimização Final CSS ===")
        out    = context.get('output', {})
        html_f = out.get('html_file')
        css_f  = out.get('css_file')

        if not (html_f and css_f and os.path.exists(html_f) and os.path.exists(css_f)):
            return context

        # --- Shadow Build (PurgeCSS com Safelist Couraçada — sempre ativo) ---
        if tool_available(CONFIG['PURGECSS_BIN']) and CONFIG['USE_PURGECSS']:
            _run_shadow_build(html_f, css_f)

        # --- LightningCSS: minifica o styles.css já substituído ---
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


def _run_shadow_build(html_f: str, css_f: str):
    """
    Estratégia Shadow Build:
      1. Coleta sources: index.html + todos os .js em scripts/
      2. Gera um purgecss.config.cjs temporário com safelist couraçada
      3. Roda PurgeCSS → gera styles.safe.css (shadow isolado)
      4. Loga a % de redução
      5. Substitui styles.css pelo shadow (mantendo o nome original)
    """
    out_dir      = os.path.dirname(css_f)        # output/styles/
    out_dir_root = os.path.dirname(out_dir)      # output/
    safe_css     = os.path.join(out_dir, 'styles.safe.css')

    # Caminhos absolutos com forward-slashes (compatível Node.js no Windows)
    abs_html = os.path.abspath(html_f).replace('\\', '/')
    abs_css  = os.path.abspath(css_f).replace('\\', '/')
    abs_safe = os.path.abspath(safe_css).replace('\\', '/')

    # Sources adicionais: todos os .js em scripts/
    content_entries = [f'"{abs_html}"']
    scripts_dir = os.path.join(out_dir_root, 'scripts')
    if os.path.isdir(scripts_dir):
        js_files = glob(os.path.join(scripts_dir, '**', '*.js'), recursive=True)
        for js in js_files:
            content_entries.append(f'"{os.path.abspath(js).replace(chr(92), "/")}"')

    content_str = ', '.join(content_entries)

    # Config JS com safelist couraçada (regex literals nativos do JS)
    config_js = f"""module.exports = {{
  content: [{content_str}],
  css: ["{abs_css}"],
  output: "{abs_safe}",
  safelist: {{
    standard: [
      /^tw-/, /^view-/, /^-tw-/, /^inline_/,
      /^btn-/, /^uploader-/, /^preview-/, /^mask-/,
      /^tool-/, /^brush-/, /^zoom-/, /^editor-/,
      /^text-/, /^bg-/, /^font-/, /^rounded-/,
      /^border-/, /^p-/, /^m-/, /^flex-/, /^grid-/,
      /^w-/, /^h-/, /^max-/, /^min-/, /^z-/,
      /^opacity-/, /^transition-/, /^duration-/, /^ease-/,
      /^hover:/, /^focus:/, /^disabled:/, /^md:/, /^lg:/, /^sm:/,
      'active', 'selected', 'loading', 'open', 'closed', 'hidden', 'visible'
    ],
    deep:   [/data-state/, /data-active/, /data-orientation/, /aria-/, /radix/],
    greedy: [/inline_/]
  }},
  defaultExtractor: content => content.match(/[\\w-/:]+(?<!:)/g) || []
}};
"""

    # Grava config temporário
    tmp_config = os.path.join(out_dir_root, '_shadow_build.config.cjs')
    with open(tmp_config, 'w', encoding='utf-8') as f:
        f.write(config_js)

    original_size = os.path.getsize(css_f)
    logger.info("  Shadow Build: rodando PurgeCSS com safelist couraçada...")

    try:
        run_command([CONFIG['PURGECSS_BIN'], '--config', tmp_config], timeout=60)
    finally:
        if os.path.exists(tmp_config):
            os.remove(tmp_config)

    if not os.path.exists(safe_css):
        logger.warning("  Shadow Build: styles.safe.css não foi gerado — mantendo CSS original")
        return

    # Relatório de redução
    shadow_size = os.path.getsize(safe_css)
    reduction   = (1 - shadow_size / original_size) * 100 if original_size > 0 else 0
    logger.info(f"  CSS original:  {original_size / 1024:.2f} KB")
    logger.info(f"  CSS shadow:    {shadow_size   / 1024:.2f} KB  (-{reduction:.1f}%)")

    # Substitui styles.css pelo shadow — mantendo o nome original
    shutil.move(safe_css, css_f)
    logger.info(f"  ✅ styles.css substituído com versão otimizada ({reduction:.1f}% menor)")


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
