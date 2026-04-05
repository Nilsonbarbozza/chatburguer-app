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
        paths  = get_paths()
        out    = context.get('output', {})
        html_f = out.get('html_file')
        css_f  = out.get('css_file')

        if not (html_f and css_f and os.path.exists(html_f) and os.path.exists(css_f)):
            return context

        # --- Shadow Build (PurgeCSS com Safelist Couraçada) ---
        if tool_available(CONFIG['PURGECSS_BIN']) and CONFIG['USE_PURGECSS']:
            _run_shadow_build(html_f, css_f)
            
            # Geração do tester.html (Ambiente de Sombra)
            if os.path.exists(paths['SAFE_STYLE_FILE']) and CONFIG['ALWAYS_GENERATE_TESTER']:
                _generate_tester_html(html_f, paths['TESTER_FILE'])

        # --- LightningCSS: minifica o styles.css original (leve) se solicitado ---
        if tool_available(CONFIG['LIGHTNINGCSS_BIN']) and CONFIG['USE_LIGHTNINGCSS'] and CONFIG['MINIFY_CSS']:
            logger.info("  LightningCSS: minificando CSS original...")
            run_command([
                CONFIG['LIGHTNINGCSS_BIN'], css_f,
                '--targets', CONFIG['LIGHTNINGCSS_TARGETS'],
                '-o', css_f, '--minify',
            ])

        if tool_available(CONFIG['PRETTIER_BIN']) and CONFIG['USE_PRETTIER']:
            logger.info("  Prettier: formatando CSS original...")
            run_command([CONFIG['PRETTIER_BIN'], '--write', css_f])

        return context


def _generate_tester_html(index_path: str, tester_path: str):
    """Copia o index.html e troca a referência do CSS para a versão segura."""
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitui styles.css por styles.safe.css (com regex para ser resiliente a aspas)
        new_content = re.sub(r'href=["\']styles/styles\.css["\']', 'href="styles/styles.safe.css"', content)
        
        # Adiciona um banner discreto no topo do tester.html para identificação
        banner = '<div style="background:#2563eb;color:white;text-align:center;padding:8px;font-family:sans-serif;font-size:12px;position:sticky;top:0;z-index:9999">AMBIENTE DE SOMBRA (OTIMIZADO) - Valide este layout antes de promover para produção</div>'
        if '<body>' in new_content:
            new_content = new_content.replace('<body>', f'<body>\n{banner}')
        elif '<body ' in new_content:
             new_content = re.sub(r'(<body[^>]*>)', r'\1\n' + banner, new_content)
        
        with open(tester_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"  ✅ Ambiente de Sombra gerado: {os.path.basename(tester_path)}")
    except Exception as e:
        logger.warning(f"  ❌ Falha ao gerar tester.html: {e}")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _run_shadow_build(html_f: str, css_f: str):
    """
    Estratégia Shadow Build:
      1. Coleta sources: index.html + todos os .js em scripts/
      2. Gera um purgecss.config.cjs temporário com Safelist Couraçada na raiz
      3. Roda PurgeCSS CLI → gera styles.safe.css (Shadow Isolado)
      4. Minifica styles.safe.css agressivamente com LightningCSS O3
      5. Loga a % de redução comparativa
    """
    out_dir      = os.path.dirname(css_f)
    out_dir_root = os.path.dirname(out_dir)
    safe_css     = os.path.join(out_dir, 'styles.safe.css')

    # Caminhos relativos (essencial para Node.js 24+ no Windows)
    rel_html = os.path.relpath(html_f).replace('\\', '/')
    rel_css  = os.path.relpath(css_f).replace('\\', '/')
    rel_safe = os.path.relpath(safe_css).replace('\\', '/')

    # Coleta de assets para análise de classes
    content_entries = [f"'{rel_html}'"]
    scripts_dir = os.path.join(out_dir_root, 'scripts')
    if os.path.isdir(scripts_dir):
        js_files = glob(os.path.join(scripts_dir, '**', '*.js'), recursive=True)
        for js in js_files:
            rel_js = os.path.relpath(js).replace('\\', '/')
            content_entries.append(f"'{rel_js}'")

    content_str = ', '.join(content_entries)

    # Config JS com Safelist Couraçada (Armored)
    config_js = f"""module.exports = {{
  content: [{content_str}],
  css: ['{rel_css}'],
  output: '{rel_safe}',
  safelist: {{
    standard: [
      /^tw-/, /^view-/, /^-tw-/, /^inline_/, /^btn-/, /^nav-/, /^modal-/,
      /^data-/, /^aria-/, /^role-/, /^is-/, /^has-/,
      'active', 'selected', 'loading', 'open', 'closed', 'hidden', 'visible', 'enabled', 'disabled'
    ],
    deep:   [/data-state/, /data-active/, /data-orientation/, /aria-/, /radix/, /next-/],
    greedy: [/inline_/, /hover:/, /focus:/, /md:/, /lg:/, /sm:/]
  }},
  defaultExtractor: content => content.match(/[\\w-/:]+(?<!:)/g) || []
}};
"""
    # Grava config temporário NA RAIZ para o Cosmiconfig achar automaticamente
    # (Não passamos --config no CLI para evitar o bug de ESM absoluto no Windows)
    tmp_config_name = 'purgecss.config.js'
    tmp_config_path = os.path.join(os.getcwd(), tmp_config_name)

    try:
        with open(tmp_config_path, 'w', encoding='utf-8') as f:
            f.write(config_js)

        original_size = os.path.getsize(css_f)
        logger.info("  Shadow Build: rodando PurgeCSS CLI (Safelist Armored bypass)...")

        # Chama PurgeCSS injetando arquivos pela CLI; safelist sera lido do purgecss.config.js automaticamente
        cmd = [CONFIG['PURGECSS_BIN'], '--css', rel_css, '--output', rel_safe, '--content', rel_html]
        if len(content_entries) > 1:
            for js_f in content_entries[1:]:
                cmd.append(js_f.strip("'"))
                
        run_command(cmd, timeout=60)
        
        if not os.path.exists(safe_css):
            logger.warning("  Shadow Build: falha ao gerar styles.safe.css")
            return

        # Minificação Extrema do Shadow
        if tool_available(CONFIG['LIGHTNINGCSS_BIN']):
            logger.info("  Shadow Build: aplicando minificação extrema O3 via LightningCSS...")
            run_command([
                CONFIG['LIGHTNINGCSS_BIN'], safe_css,
                '--targets', CONFIG['LIGHTNINGCSS_TARGETS'],
                '-o', safe_css, '--minify'
            ])

        shadow_size = os.path.getsize(safe_css)
        reduction   = (1 - shadow_size / original_size) * 100 if original_size > 0 else 0
        logger.info(f"  CSS original:  {original_size / 1024:.2f} KB")
        logger.info(f"  CSS shadow:    {shadow_size   / 1024:.2f} KB  (-{reduction:.1f}%)")
        logger.info(f"  ✅ Shadow Build concluído: styles.safe.css disponível para tester.html")

    except Exception as e:
        logger.warning(f"  Shadow Build: Erro na execução: {e}")
    finally:
        if os.path.exists(tmp_config_path):
            os.remove(tmp_config_path)


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
