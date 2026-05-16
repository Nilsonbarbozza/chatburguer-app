import time
import asyncio
import aiohttp
import logging
from curl_cffi.requests import AsyncSession as CurlCffiSession
from fastapi import HTTPException

# Usaremos o process_pool global do routes.py? É melhor injetar o loop e o pool, 
# ou usar importações locais. Para evitar acoplamento circular, vamos aceitar o pool como argumento.
from core.stages.dataclear import run_dataclear_job
from agentic_api.schemas import Archetype

logger = logging.getLogger("WaterfallExtractor")

GOOGLEBOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

async def _fetch_aiohttp(url: str, timeout: int) -> str:
    """L0: Rápido, mas vulnerável a WAF."""
    connect_timeout = min(10, timeout)
    sock_read_timeout = min(10, timeout)
    timeout_config = aiohttp.ClientTimeout(total=timeout, connect=connect_timeout, sock_read=sock_read_timeout)
    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        async with session.get(url, headers=GOOGLEBOT_HEADERS) as response:
            if response.status in (401, 403, 429, 503):
                raise HTTPException(status_code=403, detail="WAF Blocked. Use force_stealth=True.")
            response.raise_for_status()
            return await response.text()

async def _fetch_curlcffi(url: str, timeout: int) -> str:
    """L12: Furtivo via TLS Spoofing."""
    async with CurlCffiSession() as session:
        response = await session.get(url, impersonate="chrome120", headers=GOOGLEBOT_HEADERS, timeout=timeout)
        if response.status_code in (401, 403, 429, 503) or "Just a moment" in response.text:
            raise HTTPException(status_code=403, detail="Advanced WAF Blocked. TLS Spoofing failed.")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"HTTP Error {response.status_code}")
        return response.text

async def _scroll_and_wait(page, max_scrolls: int = 5) -> int:
    """
    Scroll progressivo com duplo critério de parada:
    1. Fundo da página atingido (altura não cresceu)
    2. Limite de scrolls atingido (teto de segurança)
    Retorna: número de scrolls executados
    """
    previous_height = 0
    scrolls_done = 0

    for i in range(max_scrolls):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)  # aguarda lazy load disparar

        current_height = await page.evaluate("document.body.scrollHeight")
        scrolls_done += 1

        if current_height == previous_height:
            logger.info(f"[SCROLL-WAIT] Fundo atingido após {scrolls_done} scroll(s).")
            break

        previous_height = current_height
        logger.debug(f"[SCROLL-WAIT] Scroll {scrolls_done}: altura {previous_height} → {current_height}")

    return scrolls_done

async def _fetch_playwright(url: str, timeout: int, archetype: str = None) -> str:
    """L34: Lento, pesado, mas renderiza JS completo."""
    from playwright.async_api import async_playwright
    logger.info(f"🚀 [PLAYWRIGHT] Iniciando renderização JS para: {url}")
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = None
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(timeout * 1000)
            page.set_default_timeout(timeout * 1000)
            # Ajustamos a espera conforme a complexidade do alvo
            wait_state = "domcontentloaded" if str(archetype) == "auction_grid" else "load"
            
            await page.goto(url, wait_until=wait_state, timeout=timeout * 1000)
            await page.wait_for_timeout(1500) # Hidratação mínima
            
            if str(archetype) == "auction_grid":
                logger.info(f"⚡ [QUANTUM-SCROLL] Expandindo viewport para captura instantânea em {url}")
                await page.evaluate('''async () => {
                    const height = document.body.scrollHeight;
                    window.scrollTo(0, height); // Um único salto para o fundo
                }''')
                # Ajusta o viewport para caber tudo (evita recortes de renderização)
                await page.set_viewport_size({"width": 1280, "height": 8000}) 
                await asyncio.sleep(1.5) # Tempo mínimo para disparo do JS de imagem

            content = await page.content()
            if "Just a moment" in content or "access denied" in content.lower():
                logger.warning(f"⚠️ [PLAYWRIGHT] WAF Detectado em {url}")
                raise HTTPException(status_code=403, detail="Advanced WAF Blocked. JS Render evasion failed.")
            logger.info(f"✅ [PLAYWRIGHT] Renderização concluída em {time.time()-t0:.2f}s")
            return content
        except Exception as e:
            logger.error(f"❌ [PLAYWRIGHT-ERROR]: {str(e)}")
            raise
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            await browser.close()

async def _run_dataclear_with_timeout(loop, process_pool, html_content, url, executor_level, config, capture_id, mission_id, timeout_seconds):
    work = loop.run_in_executor(process_pool, run_dataclear_job, html_content, url, executor_level, config, capture_id, mission_id)
    return await asyncio.wait_for(work, timeout=timeout_seconds)

def _json_safe(obj: object, *, _depth: int = 0, _max_depth: int = 6):
    if _depth >= _max_depth:
        return str(obj)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_json_safe(x, _depth=_depth + 1) for x in obj]
    if isinstance(obj, dict):
        safe = {}
        for k, v in obj.items():
            safe[str(k)] = _json_safe(v, _depth=_depth + 1)
        return safe
    return str(obj)

class WaterfallExtractor:
    def __init__(self, process_pool):
        self.process_pool = process_pool

    def _is_auction_grid(self, html: str) -> bool:
        """
        Detecta automaticamente se o HTML é de um site de leilão.
        Threshold calibrado para evitar falsos positivos em e-commerce.
        """
        import re
        monetary_hits = len(re.findall(r'R\$\s*[\d.,]+', html))
        date_hits     = len(re.findall(r'\d{2}/\d{2}/\d{4}', html))
        auction_hits  = len(re.findall(
            r'(?:leil[ãa]o|lote|arrema[tc]|lance|judicial|extrajudicial)',
            html, re.I
        ))
        return monetary_hits >= 8 and date_hits >= 3 and auction_hits >= 3

    async def extract(self, url: str, render_js: bool, force_stealth: bool, archetype: str, fidelity_threshold: float, capture_id: str = "agentic-api-sync"):
        timeout_seconds = 45 if render_js else 15
        
        if render_js:
            executor_used = "L34-playwright"
        elif force_stealth:
            executor_used = "L12-curlcffi"
        else:
            executor_used = "L0-aiohttp"
            
        async def fetch_strategy():
            if render_js:
                return await _fetch_playwright(url, timeout_seconds, archetype)
            elif force_stealth:
                return await _fetch_curlcffi(url, timeout_seconds)
            else:
                return await _fetch_aiohttp(url, timeout_seconds)
                
        html_content = await asyncio.wait_for(fetch_strategy(), timeout=timeout_seconds)
        
        if archetype != Archetype.HUB and archetype != Archetype.AUCTION_GRID:
            if self._is_auction_grid(html_content):
                logger.info(f"🕵️ [HEURÍSTICA] Grid de leilão detectado automaticamente. Mudando arquétipo para AUCTION_GRID.")
                archetype = Archetype.AUCTION_GRID

        config = {
            "archetype": archetype,
            "fidelity_threshold": fidelity_threshold,
            "allowed_domains": "*"
        }
        
        loop = asyncio.get_running_loop()
        clear_result = await _run_dataclear_with_timeout(
            loop=loop,
            process_pool=self.process_pool,
            html_content=html_content,
            url=url,
            executor_level=executor_used,
            config=config,
            capture_id=capture_id,
            mission_id="agentic-mission",
            timeout_seconds=timeout_seconds,
        )
        if clear_result.get("waf_blocked"):
            raise HTTPException(status_code=403, detail="Honeypot WAF Detectado pela Engenharia Reversa HTML.")
            
        entries = clear_result.get("dataset_entries", [])
        markdown_body = ""
        semantic_chunks = []
        hub_items = None
        
        if entries:
            entry = entries[0]
            data = entry.get("data", {})
            markdown_body = data.get("markdown_body", "")
            semantic_chunks = _json_safe(data.get("semantic_chunks", []))
            hub_items = _json_safe(data.get("hub_items", None))
        
        # --- O GATILHO FANTASMA (OS-014: Auto-Healing) ---
        is_ghost = False
        
        needs_l34 = (
            (archetype == Archetype.AUCTION_GRID) and (
                not hub_items 
                or len(hub_items) == 0
                or all(not (item.get('links_vital', {}) or {}).get('image') for item in (hub_items or []))
            )
        )

        if needs_l34 and executor_used != "L34-playwright":
            logger.info(f"[ESCALATION] Condição L34 ativada para {url}: items={len(hub_items) if hub_items else 0}")
            is_ghost = True
        elif archetype != Archetype.HUB and archetype != Archetype.AUCTION_GRID:
            is_ghost = not semantic_chunks or len(markdown_body) < 300

        # Se WAF explícito retornou challenge page (que passou no fetch mas falhou no parser), o markdown_body será lixo ou waf detect.
        # No L0, o cloudflare challenge pode passar pelo aiohttp com 200/403. 
        # O Playwright será chamado no auto_fallback.
        if is_ghost and executor_used != "L34-playwright":
            logger.warning(f"⚠️ [OS-014] Fantasma SPA detectado em {url}. Escalonando para L34 (Playwright)...")
            try:
                html_content_pesado = await asyncio.wait_for(_fetch_playwright(url, timeout_seconds, archetype), timeout=timeout_seconds + 5)
                executor_used = "L34-playwright-auto_fallback"
            except asyncio.TimeoutError:
                logger.error(f"❌ [TIMEOUT-DEAD-SWITCH] Playwright travou em {url} e foi abatido.")
                raise HTTPException(status_code=504, detail="Playwright fallthrough timeout.")
            
            clear_result = await _run_dataclear_with_timeout(
                loop=loop,
                process_pool=self.process_pool,
                html_content=html_content_pesado,
                url=url,
                executor_level=executor_used,
                config=config,
                capture_id=f"{capture_id}-fallback",
                mission_id="agentic-mission",
                timeout_seconds=timeout_seconds,
            )
            
            entries = clear_result.get("dataset_entries", [])
            if entries:
                entry = entries[0]
                data = entry.get("data", {})
                markdown_body = data.get("markdown_body", "")
                semantic_chunks = _json_safe(data.get("semantic_chunks", []))
                hub_items = _json_safe(data.get("hub_items", None))
                
        return {
            "markdown_body": markdown_body,
            "semantic_chunks": semantic_chunks,
            "hub_items": hub_items,
            "executor_used": executor_used,
            "waf_blocked": False
        }
