"""
core/stages/javascript.py
Stage 6 — Extração e bundling de scripts inline → scripts/main.js
"""
import os
import logging
from typing import Dict, Any, List, Tuple

from bs4 import BeautifulSoup
from core.pipeline import ProcessorStage
from core.config   import CONFIG, get_paths
from core.utils    import save_file, setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class JavaScriptExtractionStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 6: JavaScript Bundling ===")

        if not CONFIG['BUNDLE_SCRIPTS']:
            logger.info("Bundling desabilitado (BUNDLE_SCRIPTS=false)")
            context['js_bundle'] = ''
            return context

        paths = get_paths()
        os.makedirs(paths['SCRIPTS_DIR'], exist_ok=True)

        soup, bundle = _extract_inline_scripts(context['soup'])

        if bundle.strip():
            save_file(paths['BUNDLE_FILE'], bundle)
            context['soup']      = _inject_bundle_reference(soup)
            context['js_bundle'] = bundle
            logger.info(f"Bundle salvo: {paths['BUNDLE_FILE']} ({len(bundle)} bytes)")
        else:
            logger.info("Nenhum script inline encontrado")
            context['js_bundle'] = ''

        return context


def _extract_inline_scripts(soup: BeautifulSoup) -> Tuple[BeautifulSoup, str]:
    blocks: List[str] = []
    skip_types = {'application/ld+json', 'application/json', 'text/template'}

    for idx, script in enumerate(soup.find_all('script'), start=1):
        if script.get('src'):
            continue
        code         = (script.string or '').strip()
        script_type  = script.get('type', 'text/javascript')
        if not code or script_type in skip_types:
            script.decompose()
            continue
        block = (
            f"/* ── Bloco inline #{idx} (type={script_type}) ── */\n"
            f";(function() {{\n{code}\n}})();\n"
        )
        blocks.append(block)
        script.decompose()

    logger.info(f"Scripts inline: {len(blocks)} blocos extraídos")
    return soup, '\n'.join(blocks)


def _inject_bundle_reference(soup: BeautifulSoup) -> BeautifulSoup:
    body = soup.body or soup
    tag  = soup.new_tag('script', src='scripts/main.js', defer=True)
    body.append(tag)
    return soup
