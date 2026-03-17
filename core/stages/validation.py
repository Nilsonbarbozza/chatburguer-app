"""
core/stages/validation.py
Stage 1 — Validação do arquivo de entrada
"""
import os
import logging
from typing import Dict, Any

from core.pipeline import ProcessorStage
from core.config   import CONFIG
from core.utils    import MAGIC_AVAILABLE, setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class ValidationStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 1: Validação ===")
        filepath = context['input_file']

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

        size_mb = os.path.getsize(filepath) / (1024 ** 2)
        if size_mb > CONFIG['MAX_FILE_SIZE_MB']:
            raise ValueError(
                f"Arquivo muito grande: {size_mb:.2f}MB (máximo: {CONFIG['MAX_FILE_SIZE_MB']}MB)"
            )

        if MAGIC_AVAILABLE:
            try:
                import magic
                mime = magic.from_file(filepath, mime=True)
                valid = ['text/html', 'text/plain', 'application/xhtml+xml']
                if mime not in valid:
                    logger.warning(f"Tipo MIME suspeito: {mime}, tentando mesmo assim")
            except Exception as e:
                logger.warning(f"Verificação MIME falhou: {e}")
        else:
            logger.warning("python-magic não disponível — verificação MIME ignorada")

        logger.info(f"Arquivo validado: {filepath} ({size_mb:.2f}MB)")
        return context
