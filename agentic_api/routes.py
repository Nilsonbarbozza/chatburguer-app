import time
import asyncio
import aiohttp
import os
import urllib.parse
from curl_cffi.requests import AsyncSession as CurlCffiSession
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from concurrent.futures import ProcessPoolExecutor

from agentic_api.schemas import FetchRequest, FetchResponse, SearchFetchRequest, SearchFetchResponse, Archetype
from agentic_api.auth import validate_api_key_and_rate_limit, atomic_debit, refund_credits
from core.stages.dataclear import run_dataclear_job
from core.executors.waterfall import WaterfallExtractor
from core.database import db
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgenticAPI")

router = APIRouter()

# Pool global para delegar o trabalho pesado de CPU (Limpeza/BeautifulSoup)
# Limitado a 4 workers para um container de 2GB RAM
process_pool = ProcessPoolExecutor(max_workers=4)

GOOGLEBOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

async def _fetch_aiohttp(url: str, timeout: int) -> str:
    """L0: Rápido, mas vulnerável a WAF."""
    # Total protege contra tarpit; connect/sock_read reduzem travas silenciosas em rede/handshake.
    connect_timeout = min(10, timeout)
    sock_read_timeout = min(10, timeout)
    timeout_config = aiohttp.ClientTimeout(
        total=timeout,
        connect=connect_timeout,
        sock_read=sock_read_timeout,
    )
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

async def _fetch_playwright(url: str, timeout: int) -> str:
    """L34: Lento, pesado, mas renderiza JS completo."""
    from playwright.async_api import async_playwright
    logger.info(f"🚀 [PLAYWRIGHT] Iniciando renderização JS para: {url}")
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = None
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(timeout * 1000)
            page.set_default_timeout(timeout * 1000)
            
            # Usamos 'commit' seguido de 'domcontentloaded' para evitar travas em scripts de rastreamento
            await page.goto(url, wait_until="commit", timeout=timeout * 1000)
            await page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
            
            # Pequeno respiro para injeção de conteúdo via JS
            await page.wait_for_timeout(1000)
            
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


async def _run_dataclear_with_timeout(
    loop: asyncio.AbstractEventLoop,
    html_content: str,
    url: str,
    executor_level: str,
    config: dict,
    capture_id: str,
    mission_id: str,
    timeout_seconds: int,
) -> dict:
    """
    Executa o DataClear no ProcessPool com timeout duro.

    Motivação: Em produção pode ocorrer hang silencioso após o fetch (ex: HTML hostil,
    parsing pesado, edge cases). Sem timeout aqui, a requisição pode ficar presa mesmo
    quando o fetch já respeita `timeout_seconds`.
    """
    work = loop.run_in_executor(
        process_pool,
        run_dataclear_job,
        html_content,
        url,
        executor_level,
        config,
        capture_id,
        mission_id,
    )
    return await asyncio.wait_for(work, timeout=timeout_seconds)


def _json_safe(obj: object, *, _depth: int = 0, _max_depth: int = 6):
    """
    Coerção defensiva para evitar travas de serialização (ex: objetos BeautifulSoup/Tag
    escapando para o payload).

    Mantém listas/dicts, converte o resto para tipos JSON-safe via `str()`.
    """
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

@router.post("/fetch", response_model=FetchResponse)
async def fetch_url(
    request: FetchRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    customer_data: dict = Depends(validate_api_key_and_rate_limit)
):
    start_time = time.time()
    url_str = str(request.url)
    customer_id = customer_data["client_name"]
    api_key = customer_data["api_key"]
    
    # 1. Regra de Negócio: Definição de Timeout, Armamento e Custo
    timeout_seconds = 45 if request.render_js else 15
    if request.render_js:
        executor_used = "L34-playwright"
        cost = 10
    elif request.force_stealth:
        executor_used = "L12-curlcffi"
        cost = 3
    else:
        executor_used = "L0-aiohttp"
        cost = 1
        
    # Faturamento Dinâmico (Debita antes de acionar)
    remaining = await atomic_debit(api_key, cost)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    # [RADAR DE FEEDBACK] Coleta de inteligência comercial
    domain = urllib.parse.urlparse(url_str).netloc
    logger.info(f"[RADAR COMERCIAL] Cliente {customer_id} está raspando o domínio principal: {domain}")
    
    # 2. O Escudo Anti-Manada (Mutex Síncrono)
    import hashlib
    import json
    url_hash = hashlib.md5(url_str.encode()).hexdigest()
    lock_key = f"lock:capture:{url_hash}"
    cache_key = f"cache:capture:{url_hash}"
    
    from core.mq.redis_manager import RedisManager
    rm = RedisManager(tenant_db_index=0)
    
    # [NOVO] Checagem preemptiva de Cache (Sucesso ou Erro Negativo)
    cached_data = await rm.client.get(cache_key)
    if cached_data:
        resp_dict = json.loads(cached_data)
        if resp_dict.get("status") == "error":
            await refund_credits(api_key, cost)
            raise HTTPException(
                status_code=resp_dict.get("status_code", 500), 
                detail=f"[NEGATIVE CACHE] {resp_dict.get('detail')}"
            )
        
        background_tasks.add_task(db.save_radar_log, customer_id, domain, "/fetch", 200)
        processing_ms = int((time.time() - start_time) * 1000)
        resp_dict["processing_ms"] = processing_ms
        resp_dict["executor_used"] = executor_used + " (cached)"
        return FetchResponse(**resp_dict)

    # 3. Tentativa de Lock (Apenas se o cache estiver vazio)
    locked = await rm.client.set(lock_key, "1", nx=True, ex=30)
    
    if locked:
        # ==========================================
        # Fluxo do Vencedor (Dono do Lock)
        # ==========================================
        try:
            extractor = WaterfallExtractor(process_pool)
            result = await extractor.extract(
                url=url_str,
                render_js=request.render_js,
                force_stealth=request.force_stealth,
                archetype=request.archetype,
                fidelity_threshold=request.fidelity_threshold,
                capture_id="agentic-api-sync"
            )
            
            background_tasks.add_task(db.save_radar_log, customer_id, domain, "/fetch", 200)
            
            processing_ms = int((time.time() - start_time) * 1000)
            
            final_response = FetchResponse(
                status="success",
                url=url_str,
                markdown_body=result["markdown_body"],
                semantic_chunks=result["semantic_chunks"],
                hub_items=result["hub_items"],
                processing_ms=processing_ms,
                executor_used=result["executor_used"]
            )
            
            # Salvar no cache e liberar lock
            await rm.client.set(cache_key, final_response.model_dump_json(), ex=300)
            await rm.client.delete(lock_key)
            return final_response
            
        except HTTPException as e:
            # Erro de WAF ou bloqueio conhecido. 
            # Registramos como erro negativo no cache por 60s para evitar que clones tentem a mesma missão suicida.
            error_data = {"status": "error", "detail": e.detail, "status_code": e.status_code}
            await rm.client.set(cache_key, json.dumps(error_data), ex=60)
            await rm.client.delete(lock_key)
            # Reembolsa créditos pois o scraper não entregou o valor prometido
            await refund_credits(api_key, cost)
            raise
        except Exception as e:
            # Reembolso por falha interna miserável
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"❌ [CRITICAL-API-ERROR]: {str(e)}\n{error_trace}")
            
            error_data = {"status": "error", "detail": str(e), "status_code": 500}
            await rm.client.set(cache_key, json.dumps(error_data), ex=60)
            await refund_credits(api_key, cost)
            await rm.client.delete(lock_key)
            if isinstance(e, asyncio.TimeoutError):
                raise HTTPException(status_code=504, detail="Gateway Timeout")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # ==========================================
        # Fluxo do Clone (Esperando no Cache)
        # ==========================================
        logger.info(f"[ANTI-MANADA] Cliente {customer_id} em aguardo (Clone) para: {url_str}")
        for _ in range(60): # Espera máxima de 30 segundos
            await asyncio.sleep(0.5)
            cached_data = await rm.client.get(cache_key)
            if cached_data:
                resp_dict = json.loads(cached_data)
                
                # Checa se é um Negative Cache (Erro registrado pelo Vencedor)
                if resp_dict.get("status") == "error":
                    await refund_credits(api_key, cost)
                    raise HTTPException(
                        status_code=resp_dict.get("status_code", 500), 
                        detail=f"[NEGATIVE CACHE] {resp_dict.get('detail')}"
                    )

                background_tasks.add_task(db.save_radar_log, customer_id, domain, "/fetch", 200)
                processing_ms = int((time.time() - start_time) * 1000)
                resp_dict["processing_ms"] = processing_ms
                resp_dict["executor_used"] = executor_used + " (cached)"
                return FetchResponse(**resp_dict)
                
        # Se expirou o tempo e o Vencedor não entregou nada
        await refund_credits(api_key, cost)
        raise HTTPException(status_code=504, detail="Timeout aguardando execução primária do Batalhão.")

@router.post("/search_and_fetch", response_model=SearchFetchResponse)
async def search_and_fetch(
    request: SearchFetchRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    customer_data: dict = Depends(validate_api_key_and_rate_limit)
):
    start_time = time.time()
    customer_id = customer_data["client_name"]
    api_key = customer_data["api_key"]
    
    # 1. Regra de Negócio: Faturamento
    if request.force_stealth:
        cost = 3
    else:
        cost = 1
        
    # Debita antes de acionar o Batalhão
    remaining = await atomic_debit(api_key, cost)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    try:
        from core.config import settings
        tavily_api_key = settings.TAVILY_API_KEY
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.tavily.com/search", json={"api_key": tavily_api_key, "query": request.query, "max_results": 2}) as resp:
                if resp.status != 200:
                    tavily_err = await resp.text()
                    raise HTTPException(status_code=502, detail=f"Tavily API Failed: {tavily_err}")
                data = await resp.json()
                urls = [r.get("url") for r in data.get("results", []) if r.get("url")]
        
        if not urls:
            raise HTTPException(status_code=404, detail="O Radar não encontrou nenhuma URL relevante para esta busca.")
            
        # [RADAR DE FEEDBACK] Coleta de inteligência comercial
        for u in urls:
            domain = urllib.parse.urlparse(u).netloc
            logger.info(f"[RADAR COMERCIAL] Cliente {customer_id} descobriu o alvo: {domain} via Tavily Radar.")
            background_tasks.add_task(db.save_radar_log, customer_id, domain, "/search_and_fetch", 200)
    
        extractor = WaterfallExtractor(process_pool)
        results = []
        urls_processed = []
        
        async def process_url(u):
            try:
                # O Radar não força render_js inicialmente, o WaterfallExtractor cuidará do fallback fantasma (L34)
                result = await extractor.extract(
                    url=u,
                    render_js=False,
                    force_stealth=request.force_stealth,
                    archetype=Archetype.BLOG,
                    fidelity_threshold=request.fidelity_threshold,
                    capture_id="agentic-api-radar"
                )
                if result["markdown_body"] or result["semantic_chunks"]:
                    results.append({
                        "url": u,
                        "markdown_body": result["markdown_body"],
                        "semantic_chunks": result["semantic_chunks"]
                    })
                    urls_processed.append(u)
            except HTTPException as e:
                logger.error(f"🚨 [RADAR-WAF] WAF/Bloqueio detectado em {u}: {e.detail}")
            except Exception as e:
                logger.error(f"Erro na extração de {u}: {e}")
                
        # Executa extração em paralelo para todas as URLs
        await asyncio.gather(*(process_url(u) for u in urls))
    
        if not results:
            raise HTTPException(status_code=404, detail="O conteúdo encontrado não passou no filtro de qualidade (Fidelidade < 0.6).")
    
        return SearchFetchResponse(
            query=request.query,
            urls_processed=urls_processed,
            processing_ms=int((time.time() - start_time) * 1000),
            results=results
        )
    except HTTPException:
        # Se for WAF, o cliente consome
        raise
    except Exception as e:
        logger.error(f"CRITICAL ERROR IN RADAR: {e}")
        # Estorno em caso de falha sistêmica
        await refund_credits(api_key, cost)
        raise HTTPException(status_code=500, detail=f"Erro Crítico no Radar: {str(e)}")
