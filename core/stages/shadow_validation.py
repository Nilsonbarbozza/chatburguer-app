"""
core/stages/shadow_validation.py
Estágio de Validação Visual (Shadow Health Check)
Utiliza Playwright para comparar index.html e tester.html.
"""
import os
import logging
import asyncio
from typing import Dict, Any

from core.pipeline import ProcessorStage
from core.config   import CONFIG, get_paths
from core.utils    import setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class ShadowValidationStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not CONFIG['USE_VALIDATION']:
            logger.info("Etapa de Validação Shadow desativada por configuração.")
            return context

        logger.info("=== ETAPA 12: Shadow Health Check (Validação Visual) ===")
        paths = get_paths()
        index_html = os.path.abspath(context.get('output', {}).get('html_file', ''))
        tester_html = os.path.abspath(paths['TESTER_FILE'])

        if not os.path.exists(tester_html):
            logger.warning("  ⚠️ tester.html não encontrado. Pulando validação.")
            return context

        try:
            from playwright.sync_api import sync_playwright
            self._run_sync_validation(index_html, tester_html)
        except ImportError:
            logger.warning("  ⚠️ Playwright não encontrado. Validação visual ignorada.")
            logger.info("  Dica: 'pip install playwright && playwright install chromium' para ativar.")
        except Exception as e:
            logger.error(f"  ❌ Erro durante a validação shadow: {e}")

        return context

    def _run_sync_validation(self, index_path: str, tester_path: str):
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 1. Check index.html (Baseline)
            logger.info(f"  Analisando Baseline: {os.path.basename(index_path)}")
            page.goto(f"file:///{index_path.replace(os.sep, '/')}")
            baseline_errors = self._capture_console_errors(page)
            
            # 2. Check tester.html (Shadow)
            logger.info(f"  Analisando Shadow: {os.path.basename(tester_path)}")
            page.goto(f"file:///{tester_path.replace(os.sep, '/')}")
            shadow_errors = self._capture_console_errors(page)

            # 3. Comparação de erros
            new_errors = [e for e in shadow_errors if e not in baseline_errors]
            if new_errors:
                logger.warning(f"  ⚠️ Detectados {len(new_errors)} novos erros no console do Shadow Build!")
                for err in new_errors:
                    logger.warning(f"    - {err}")
            else:
                logger.info("  ✅ Nenhum erro de recurso detectado no Shadow Build.")

            browser.close()

    def _capture_console_errors(self, page) -> list:
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(err.message))
        # Wait a bit for async resources
        page.wait_for_timeout(2000) 
        return errors
