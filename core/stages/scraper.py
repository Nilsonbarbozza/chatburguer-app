"""
core/stages/scraper.py
Stage 0 — Coleta ativa de HTML usando Playwright (Headless Browser)
Garante que Lazy Loading e JS dinâmico sejam capturados.
"""
import logging
import time
from typing import Dict, Any
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
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
            import os
            profile_dir = os.path.expanduser("~/.process-cloner/browser_profile")
            
            with sync_playwright() as p:
                logger.info(f"Iniciando navegador Chromium com Sessão Persistente em {profile_dir}...")
                
                # --- STEALTH CONFIG (GRAU MILITAR) ---
                # A Reuters/Akamai detecta a versão 121 como "velha" para automação.
                # Vamos usar a assinatura do Chrome 124, a mais recente e estável.
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certifcate-errors"
                ]

                # --- PROTOCOLO SHADOW: SIMULAÇÃO DE ORIGEM GOOGLE ---
                # Enganamos o WAF fazendo-o acreditar que o tráfego vem de uma busca orgânica.
                extra_headers = {
                    "Referer": "https://www.google.com/search?q=reuters+world+news",
                    "Upgrade-Insecure-Requests": "1"
                }

                browser_context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    args=args,
                    extra_http_headers=extra_headers
                )
                
                if browser_context.pages:
                    page = browser_context.pages[0]
                else:
                    page = browser_context.new_page()
                
                # --- CAMADA STEALTH (ANTI-FINGERPRINTING) ---
                Stealth().apply_stealth_sync(page)
                
                # Otimização para modo Dataset: Bloqueia imagens e fontes para economizar banda/tempo
                if context.get('mode') == 'dataset':
                    logger.info("Modo Dataset detectado: Bloqueando download de imagens, fontes e mídia...")
                    page.route("**/*", lambda route: route.abort() 
                               if route.request.resource_type in ["image", "font", "media"] 
                               else route.continue_())
                
                # --- SENSORES DE DETECÇÃO WAF ---
                def check_waf(response):
                    if response and response.status in [403, 429]:
                        logger.error(f"🚨 INTERCEPTAÇÃO DETECTADA: Status {response.status}. IP bloqueado por WAF (Akamai/Firewall).")
                        return True
                    return False

                # Navega até a página com timeout protegido
                logger.info(f"Acessando URL: {url}...")
                response = None
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    if check_waf(response):
                        context['error'] = "WAF_BLOCK"
                        return context
                except Exception as e:
                    logger.warning(f"Timeout ao abrir página. Prosseguindo: {e}")
                
                # --- GHOST CURSOR (SIMULAÇÃO BIOMÉTRICA) ---
                import random
                import math

                def human_mouse_move(p, target_x, target_y):
                    """Move o mouse usando uma curva de Bezier para simular aceleração humana."""
                    curr_x, curr_y = 100, 100 # Início arbitrário
                    steps = random.randint(15, 25)
                    # Pontos de controle para a curva
                    cp1_x, cp1_y = curr_x + random.randint(-50, 200), curr_y + random.randint(-50, 200)
                    cp2_x, cp2_y = target_x - random.randint(-50, 200), target_y - random.randint(-50, 200)
                    
                    for i in range(steps + 1):
                        t = i / steps
                        # Bezier cúbica
                        x = (1-t)**3 * curr_x + 3*(1-t)**2*t*cp1_x + 3*(1-t)*t**2*cp2_x + t**3*target_x
                        y = (1-t)**3 * curr_y + 3*(1-t)**2*t*cp1_y + 3*(1-t)*t**2*cp2_y + t**3*target_y
                        p.mouse.move(x, y)
                        time.sleep(random.uniform(0.01, 0.03))

                # Realiza movimentos aleatórios de "leitura"
                logger.info("[MIMICRY] Simulando biometria de mouse (Curvas de Bézier)...")
                human_mouse_move(page, random.randint(300, 800), random.randint(200, 600))
                time.sleep(random.uniform(1.0, 2.5))

                # --- Hook de Interação Inicial (Bypass de Bloqueios e GDPR) ---
                import re
                try:
                    consent_frame = page.frame_locator('iframe[src*="consent.google.com"], iframe[src*="consensu.org"]')
                    frame_accept = consent_frame.locator('button:has-text("Aceitar"), button:has-text("Accept"), button:has-text("Concordo"), button:has-text("Salli")').first
                    
                    if frame_accept.is_visible(timeout=5000):
                        page.mouse.click(10, 10) # Foco fake
                        frame_accept.click()
                        logger.info("Popup GDPR bypassado.")
                        time.sleep(2)
                except:
                    pass

                # --- SCROLL HEURÍSTICO ADAPTATIVO (ANTI-REGRESSÃO) ---
                def adaptive_scroll(p):
                    logger.info("[MIMICRY] Executando scroll adaptativo...")
                    
                    # 1. Detectar se existe um container interno (Google Maps / Reviews)
                    panel = p.locator('div[role="main"]').first
                    use_container = False
                    
                    try:
                        if panel.is_visible(timeout=2000):
                            # Move o mouse para cima do painel para que o scroll afete o container certo
                            box = panel.bounding_box()
                            if box:
                                p.mouse.move(box['x'] + 50, box['y'] + 50)
                                use_container = True
                                logger.info("Container 'role=main' detectado. Focando scroll biométrico no painel lateral.")
                    except:
                        pass
                    
                    current_scroll = 0
                    limit = 5000 # Segurança para não scrollar infinito
                    
                    while current_scroll < limit:
                        step = random.randint(400, 800)
                        current_scroll += step
                        
                        # Se estivermos no Maps/SPA, o scroll deve ser via wheel sobre o painel
                        p.mouse.wheel(0, step)
                        
                        # Tática de Overshoot (Ajuste de visão humano)
                        if random.random() > 0.7:
                            time.sleep(random.uniform(0.3, 0.8))
                            p.mouse.wheel(0, -random.randint(50, 150))
                        
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        # Check de parada: se a altura não mudar mais, paramos
                        new_height = p.evaluate("document.body.scrollHeight")
                        if current_scroll >= new_height and not use_container:
                            break
                
                adaptive_scroll(page)
                
                # --- EXTRAÇÃO E CHECAGEM DE INTEGRIDADE ---
                content_html = page.content()
                
                # Proteção contra "Casca Vazia" (WAF Block Silencioso)
                if len(content_html) < 3000:
                    logger.warning("Conteúdo extraído suspiciously pequeno (Block detectado?). Tentando aguardar Network Idle...")
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                        content_html = page.content()
                    except:
                        pass
                
                context['html'] = content_html
                logger.info(f"✅ HTML extraído com sucesso: {len(context['html'])} bytes")
                
                # Aguarda estabilização final da rede, mas não colapsa se a rede nunca parar (ex: Google Maps)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    logger.info("Rede não estabilizou completamente (comum em mapas/carrosséis). Extraindo assim mesmo.")
                
                # Clica no botão "Mais" para ler a descrição completa em SPAs e Reviews
                try:
                    more_btns = page.get_by_role("button", name=re.compile(r"^Mais$|^More$|Expandir", re.IGNORECASE)).all()
                    clicked = False
                    for b in more_btns:
                        if b.is_visible(timeout=500):
                            b.click(timeout=1000)
                            time.sleep(0.3)
                            clicked = True
                    if clicked: logger.info("Textos truncados expandidos automaticamente.")
                except Exception:
                    pass

                # Breve pausa para garantir que scripts de carrossel terminem de renderizar
                time.sleep(2)
                
                # --- Captura Otimizada (Isolamento Estrutural no Playwright) ---
                # O conteúdo real do Maps/SPAs fica num painel lateral (Aria role 'main').
                # Capturamos HTML APENAS do painel principal para expurgar massivamente o ruído global do body.
                try:
                    panel = page.locator('div[role="main"]').first
                    if panel.is_visible(timeout=1000):
                        panel_html = panel.inner_html()
                        context['html'] = f"<div role='main'>{panel_html}</div>" # Preserva o wrapper para o Soup
                        logger.info("Main Content perfeitamente isolado e extraído na origem!")
                    else:
                        raise Exception("Main content não visível ou ausente.")
                except Exception:
                    # Fallback universal para páginas comuns (como Ebay) onde a tela toda é útil
                    context['html'] = page.content()
                
                # Se não houver uma base_url já definida, usamos a URL atual
                if not context.get('base_url'):
                    context['base_url'] = url
                    
                logger.info(f"✅ HTML extraído com sucesso: {len(context['html'])} bytes")
                browser_context.close()
                
        except Exception as e:
            logger.error(f"❌ Falha crítica no ScraperStage: {e}")
            # Em caso de falha, o pipeline continuará tentando ler via LoadingStage (arquivo local)
            
        return context

    def _auto_scroll(self, page):
        """
        Executa scroll dinâmico para acionar Lazy Loading massivo.
        Adaptado para rolar painéis internos de SPAs em vez de tentar rolar bodys travados (overflow-hidden).
        """
        page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 800; // Passo do scroll
                    
                    // Estrutura Anti-SPA: Tenta achar um painel lateral, senão rola a janela global
                    let scrollContainer = document.querySelector('div[role="main"]') || window;
                    
                    let timer = setInterval(() => {
                        let scrollHeight = scrollContainer.scrollHeight || document.body.scrollHeight;
                        
                        if (scrollContainer === window) {
                            window.scrollBy(0, distance);
                        } else {
                            scrollContainer.scrollBy(0, distance);
                        }
                        
                        totalHeight += distance;
                        
                        // Encerra ao atingir o fim real ou limite de segurança (30.000px)
                        if(totalHeight >= scrollHeight || totalHeight > 30000){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 150); // Velocidade do motor de scroll
                });
                
                // Retorna a view para o topo do scroll container para indexar correto as imagens
                let container = document.querySelector('div[role="main"]');
                if (container) container.scrollTo(0, 0);
                else window.scrollTo(0, 0);
            }
        """)
