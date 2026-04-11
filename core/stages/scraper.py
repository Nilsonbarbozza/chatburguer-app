"""
core/stages/scraper.py
Stage 0 — Coleta ativa de HTML usando Playwright (Headless Browser)
Garante que Lazy Loading e JS dinâmico sejam capturados.
"""
import logging
import time
from typing import Dict, Any
from playwright.sync_api import sync_playwright
from core.pipeline import ProcessorStage

logger = logging.getLogger('html_processor')

class ScraperStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        url = context.get('url')
        if not url:
            logger.info("Nenhuma URL fornecida no contexto. Pulando estágio de Scraping.")
            return context

        logger.info(f"=== ETAPA 0: Scraper Ativo (Playwright) — {url} ===")
        
        try:
            with sync_playwright() as p:
                logger.info("Iniciando navegador Chromium...")
                browser = p.chromium.launch(headless=True)
                
                # Configura context com User-Agent comum para evitar bloqueios
                browser_context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = browser_context.new_page()
                
                # Navega e aguarda carregamento inicial até a rede estabilizar
                logger.info(f"Acessando URL: {url} (aguardando networkidle)...")
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                # --- Lógica de Auto-Scroll para acionar Lazy Loading ---
                logger.info("Executando Auto-Scroll para ativar Lazy Loading e componentes dinâmicos...")
                self._auto_scroll(page)
                
                # Aguarda estabilização final da rede após o scroll
                page.wait_for_load_state("networkidle")
                
                # Breve pausa para garantir que scripts de carrossel terminem de renderizar
                time.sleep(2)
                
                # Captura o HTML renderizado final
                context['html'] = page.content()
                
                # Se não houver uma base_url já definida, usamos a URL atual
                if not context.get('base_url'):
                    context['base_url'] = url
                    
                logger.info(f"✅ HTML extraído com sucesso: {len(context['html'])} bytes")
                browser.close()
                
        except Exception as e:
            logger.error(f"❌ Falha crítica no ScraperStage: {e}")
            # Em caso de falha, o pipeline continuará tentando ler via LoadingStage (arquivo local)
            
        return context

    def _auto_scroll(self, page):
        """Rola a página gradualmente para forçar o carregamento de ativos lazy-load."""
        page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 400; // Distância por pulo
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight || totalHeight > 10000){ // Limite de 10k pixels por segurança
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
                window.scrollTo(0, 0); // Volta ao topo para os outros estágios
            }
        """)
