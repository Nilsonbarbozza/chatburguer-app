"""
core/stages/output.py
Stage 9 — Geração dos arquivos finais (index.html + styles/styles.css)
"""
import os
import re
import logging
from typing import Dict, Any

import lxml.html
import lxml.etree as etree
from bs4 import BeautifulSoup
from core.pipeline import ProcessorStage
from core.config   import CONFIG, get_paths
from core.utils    import save_file, tool_available, run_command, setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class OutputStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 9: Geração de Saída ===")
        paths = get_paths()

        os.makedirs(paths['STYLES_DIR'], exist_ok=True)
        os.makedirs(paths['OUT_DIR'],    exist_ok=True)

        # Salva CSS
        save_file(paths['STYLE_FILE'], context.get('css', ''))

        # Formata e salva HTML
        raw_html   = context['soup'].decode()
        final_html = _format_html(raw_html)
        html_path  = os.path.join(paths['OUT_DIR'], 'index.html')
        save_file(html_path, final_html)

        context['output'] = {
            'html_file':  html_path,
            'css_file':   paths['STYLE_FILE'],
            'js_bundle':  paths['BUNDLE_FILE'] if context.get('js_bundle') else None,
            'images_dir': paths['IMAGES_DIR'],
        }
        return context


def _format_html(html: str) -> str:
    binary = CONFIG['PRETTIER_BIN']
    if tool_available(binary) and CONFIG['USE_PRETTIER']:
        result = run_command(
            [binary, '--parser', 'html', '--print-width', '120', '--tab-width', '2'],
            stdin=html,
            timeout=60,
        )
        if result is not None:
            logger.info("HTML formatado pelo Prettier")
            return result
        logger.warning("Prettier falhou — fallback lxml")

    return _format_html_lxml(html)


def _format_html_lxml(html: str) -> str:
    try:
        parser    = lxml.html.HTMLParser(remove_blank_text=True)
        tree      = lxml.html.fromstring(html, parser=parser)
        lxml.etree.indent(tree, space="  ")
        formatted = etree.tostring(tree, pretty_print=True, encoding='unicode', method='html')

        inline_tags = ['h1','h2','h3','h4','h5','h6','p','title','span',
                       'a','label','button','i','b','strong','em','small']
        for tag in inline_tags:
            formatted = re.sub(
                rf'<{tag}([^>]*)>\s*(.*?)\s*</{tag}>',
                rf'<{tag}\1>\2</{tag}>',
                formatted, flags=re.DOTALL,
            )

        lines = [line.rstrip() for line in formatted.split('\n')]
        return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"lxml formatter falhou: {e} — usando bs4.prettify")
        return BeautifulSoup(html, 'lxml').prettify(formatter='html')
