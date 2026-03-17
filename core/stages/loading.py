"""
core/stages/loading.py
Stage 2 — Leitura do HTML e construção do BeautifulSoup
"""
import logging
from typing import Dict, Any

from bs4 import BeautifulSoup
from core.pipeline import ProcessorStage
from core.utils    import setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class LoadingStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 2: Carregamento ===")
        with open(context['input_file'], 'r', encoding='utf-8', errors='replace') as f:
            context['html'] = f.read()
        context['soup'] = BeautifulSoup(context['html'], 'lxml')
        logger.info(f"HTML carregado: {len(context['html'])} bytes")
        return context
