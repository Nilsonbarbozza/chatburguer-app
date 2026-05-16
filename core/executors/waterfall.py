import os
import time
import asyncio
import random
import aiohttp
import logging
import requests as sync_requests
from curl_cffi.requests import AsyncSession as CurlCffiSession
from fastapi import HTTPException

from core.stages.dataclear import run_dataclear_job
from agentic_api.schemas import Archetype

logger = logging.getLogger("WaterfallExtractor")

# === WEBSHARE PROXY POOL ===
def _load_webshare_proxies() -> list:
    """Carrega a lista de proxies da Webshare API no startup."""
    api_key = os.getenv("PROXIES_SX_API_KEY", "")
    if not api_key:
        logger.warning("[PROXY] PROXIES_SX_API_KEY vazio. Operando sem proxy.")
        return []
    try:
        r = sync_requests.get(
            "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=25",
            headers={"Authorization": f"Token {api_key}"},
            timeout=10
        )
        if r.status_code == 200:
            proxies = []
            for px in r.json().get('results', []):
                user = px.get('username', '')
                pwd = px.get('password', '')
                host = px.get('proxy_address', '')
                port = px.get('port', '')
                if user and host:
                    proxies.append(f"http://{user}:{pwd}@{host}:{port}")
            logger.info(f"[PROXY] Webshare: {len(proxies)} proxies carregados.")
            return proxies
        else:
            logger.warning(f"[PROXY] Webshare API retornou {r.status_code}")
            return []
    except Exception as e:
        logger.warning(f"[PROXY] Falha ao carregar Webshare: {e}")
        return []

WEBSHARE_PROXIES = _load_webshare_proxies()

def _get_proxy() -> str | None:
    """Retorna um proxy aleatório do pool, ou None se vazio."""
    return random.choice(WEBSHARE_PROXIES) if WEBSHARE_PROXIES else None

# === HEADERS POR NÍVEL DE EVASÃO ===

# L0: Headers legítimos de crawler (sem pretensão de ser navegador)
GOOGLEBOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# L12: Headers sincronizados com impersonate="chrome120"
# Elimina a "Assinatura Quimera" (TLS de Chrome + headers de Bot)
CHROME_120_HEADERS = {
    "accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "cache-control": "max-age=0",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
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
    """L12: Furtivo via TLS Spoofing + Headers Chrome 120 + Webshare Proxy."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    
    headers = {**CHROME_120_HEADERS, "referer": f"https://www.google.com/search?q={domain}"}
    proxy = _get_proxy()
    
    if proxy:
        logger.info(f"[L12] Usando proxy: {proxy.split('@')[-1] if '@' in proxy else 'direct'}")
    
    async with CurlCffiSession() as session:
        response = await session.get(
            url, impersonate="chrome120", headers=headers,
            proxy=proxy, timeout=timeout
        )
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
        # Proxy Webshare para L34
        proxy_url = _get_proxy()
        launch_opts = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if proxy_url:
            from urllib.parse import urlparse as _urlparse
            _p = _urlparse(proxy_url)
            launch_opts["proxy"] = {
                "server": f"http://{_p.hostname}:{_p.port}",
                "username": _p.username,
                "password": _p.password,
            }
            logger.info(f"[L34] Usando proxy: {_p.hostname}:{_p.port}")
        
        browser = await p.chromium.launch(**launch_opts)
        context = None
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(timeout * 1000)
            page.set_default_timeout(timeout * 1000)
            # Ajustamos a espera conforme a complexidade do alvo
            # Para Grids de Leilão (MegaLeiloes), precisamos de carga total da rede (networkidle)
            wait_state = "networkidle" if str(archetype) == "auction_grid" else "load"
            
            await page.goto(url, wait_until=wait_state, timeout=timeout * 1000)
            await page.wait_for_timeout(3000) # Hidratação estendida
            
            if str(archetype) == "auction_grid":
                logger.info(f"⚡ [QUANTUM-SCROLL] Expandindo viewport para captura profunda em {url}")
                await page.evaluate('''async () => {
                    const height = document.body.scrollHeight;
                    window.scrollTo(0, height); 
                }''')
                await page.set_viewport_size({"width": 1280, "height": 10000}) 
                await asyncio.sleep(3.0) # Tempo para lazy load de imagens e cards dinâmicos

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
        
        # === CASCATA L0 → L12 → L34 ===
        html_content = None
        executor_used = None
        
        if render_js:
            # Pedido explícito de JS rendering → direto para L34
            executor_used = "L34-playwright"
            html_content = await asyncio.wait_for(
                _fetch_playwright(url, timeout_seconds, archetype), timeout=timeout_seconds
            )
        elif force_stealth:
            # Pedido explícito de stealth → direto para L12
            executor_used = "L12-curlcffi"
            html_content = await asyncio.wait_for(
                _fetch_curlcffi(url, timeout_seconds), timeout=timeout_seconds
            )
        else:
            # CASCATA AUTOMÁTICA: L0 → L12 → (L34 via Auto-Healing)
            # Tentativa 1: L0 (aiohttp — rápido, leve)
            try:
                executor_used = "L0-aiohttp"
                html_content = await asyncio.wait_for(
                    _fetch_aiohttp(url, timeout_seconds), timeout=timeout_seconds
                )
            except Exception as e:
                logger.warning(f"[CASCADE] L0 falhou para {url}: {type(e).__name__}. Escalando para L12...")
                html_content = None
            
            # Tentativa 2: L12 (curlcffi — TLS Chrome + Headers sincronizados)
            if html_content is None:
                try:
                    executor_used = "L12-curlcffi"
                    html_content = await asyncio.wait_for(
                        _fetch_curlcffi(url, timeout_seconds), timeout=timeout_seconds
                    )
                except Exception as e:
                    logger.warning(f"[CASCADE] L12 falhou para {url}: {type(e).__name__}. L34 será acionado pelo Auto-Healing.")
                    # Se L12 também falhou, precisamos de HTML mínimo para o dataclear detectar WAF
                    html_content = "<html><body>WAF Challenge - Cascade Exhausted</body></html>"
        
        
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
        # === CASCATA DE AUTO-HEALING: WAF detectado → L12 → L34 ===
        is_ghost = False
        if clear_result.waf_detected:
            if "L0" in executor_used:
                # WAF no L0: tentar L12 (Chrome TLS) antes do pesado L34
                logger.warning(f"[CASCADE] WAF detectado em {executor_used}. Escalando para L12 (Chrome TLS)...")
                try:
                    html_content = await asyncio.wait_for(
                        _fetch_curlcffi(url, timeout_seconds), timeout=timeout_seconds
                    )
                    executor_used = "L12-curlcffi-cascade"
                    
                    # Reprocessar com o HTML do L12
                    clear_result = await _run_dataclear_with_timeout(
                        loop=loop, process_pool=self.process_pool,
                        html_content=html_content, url=url,
                        executor_level=executor_used, config=config,
                        capture_id=f"{capture_id}-l12", mission_id="agentic-mission",
                        timeout_seconds=timeout_seconds,
                    )
                    
                    if clear_result.waf_detected:
                        logger.warning(f"[CASCADE] WAF persiste em L12. Escalando para L34...")
                        is_ghost = True
                    else:
                        logger.info(f"[CASCADE] L12 BYPASS SUCESSO para {url}")
                        # Reextrair dados do novo resultado
                        entries = clear_result.dataset_entries
                        if entries:
                            entry = entries[0]
                            data = entry.get("data", {})
                            markdown_body = data.get("markdown_body", "")
                            semantic_chunks = _json_safe(data.get("semantic_chunks", []))
                            hub_items = _json_safe(data.get("hub_items", None))
                except Exception as e:
                    logger.warning(f"[CASCADE] L12 falhou ({type(e).__name__}). Escalando para L34...")
                    is_ghost = True
                    
            elif "L34" not in executor_used:
                # WAF no L12: escalar para L34
                logger.warning(f"[CASCADE] WAF detectado em {executor_used}. Escalando para L34...")
                is_ghost = True
            else:
                raise HTTPException(status_code=403, detail="Honeypot WAF Detectado pela Engenharia Reversa HTML (Nivel Maximo Atingido).")
            
        entries = clear_result.dataset_entries
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
        if not is_ghost:
            needs_l34 = (
                (archetype == Archetype.AUCTION_GRID) and (
                    not hub_items 
                    or len(hub_items) == 0
                    or all(not (item.get('links_vital', {}) or {}).get('image') for item in (hub_items or []))
                )
            )

            if needs_l34 and "L34" not in executor_used:
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
                html_content_pesado = await asyncio.wait_for(_fetch_playwright(url, timeout_seconds + 15, archetype), timeout=timeout_seconds + 20)
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
            
            entries = clear_result.dataset_entries
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
