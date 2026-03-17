"""
core/stages/tailwind.py
Stage 8 — Integração opcional do Tailwind CDN
Ativado via: USE_TAILWIND=true no .env
NÃO contém hardcodes de sites específicos.
"""
import logging
from typing import Dict, Any

from core.pipeline import ProcessorStage
from core.config   import CONFIG
from core.utils    import setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class TailwindIntegrationStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not CONFIG.get('USE_TAILWIND', False):
            logger.info("=== ETAPA 8: Tailwind desabilitado (USE_TAILWIND=false) ===")
            return context

        logger.info("=== ETAPA 8: Integração Tailwind CDN ===")
        soup = context['soup']

        if soup.head:
            cdn_script = soup.new_tag('script', src="https://cdn.tailwindcss.com")
            config_script = soup.new_tag('script')
            config_script.string = (
                "\n      tailwind.config = {\n"
                "        prefix: 'tw-',\n"
                "        corePlugins: { preflight: false },\n"
                "      };\n    "
            )
            soup.head.append(cdn_script)
            soup.head.append(config_script)
            logger.info("Tailwind CDN injetado (prefix: tw-, preflight: false)")

        context['soup'] = soup
        return context
