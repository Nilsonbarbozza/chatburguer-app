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
        
        # Se o HTML já estiver presente (vido do Scraper), pulamos a leitura de arquivo
        if not context.get('html'):
            if not context.get('input_file'):
                raise ValueError("Nenhum arquivo de entrada ou HTML fornecido.")
                
            with open(context['input_file'], 'r', encoding='utf-8', errors='replace') as f:
                context['html'] = f.read()
                logger.info(f"HTML carregado via arquivo: {context['input_file']}")
        else:
            logger.info("Usando HTML pré-carregado do estágio anterior.")
            
        context['soup'] = BeautifulSoup(context['html'], 'lxml')
        
        # Tenta descobrir base_url via tag <base> se não fornecido
        if not context.get('base_url'):
            base_tag = context['soup'].find('base')
            if base_tag and base_tag.get('href'):
                context['base_url'] = base_tag['href']
                logger.info(f"Base URL detectada via HTML: {context['base_url']}")

        logger.info(f"HTML carregado: {len(context['html'])} bytes")
        return context
