import time
import asyncio
import aiohttp
import os
import urllib.parse
from curl_cffi.requests import AsyncSession as CurlCffiSession
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from concurrent.futures import ProcessPoolExecutor

from agentic_api.schemas import FetchRequest, FetchResponse, SearchFetchRequest, SearchFetchResponse
from agentic_api.auth import validate_api_key_and_rate_limit, atomic_debit, refund_credits
from core.stages.dataclear import run_dataclear_job
from core.database import db
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgenticAPI")

router = APIRouter()

# Pool global para delegar o trabalho pesado de CPU (Limpeza/BeautifulSoup)
# Limitado a 4 workers para um container de 2GB RAM
process_pool = ProcessPoolExecutor(max_workers=4)

async def _fetch_aiohttp(url: str, timeout: int) -> str:
    """L0: Rápido, mas vulnerável a WAF."""
    timeout_config = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        async with session.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as response:
            if response.status in (401, 403, 429, 503):
                raise HTTPException(status_code=403, detail="WAF Blocked. Use force_stealth=True.")
            response.raise_for_status()
            return await response.text()

async def _fetch_curlcffi(url: str, timeout: int) -> str:
    """L12: Furtivo via TLS Spoofing."""
    async with CurlCffiSession() as session:
        response = await session.get(url, impersonate="chrome120", timeout=timeout)
        if response.status_code in (401, 403, 429, 503) or "Just a moment" in response.text:
            raise HTTPException(status_code=403, detail="Advanced WAF Blocked. TLS Spoofing failed.")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"HTTP Error {response.status_code}")
        return response.text

async def _fetch_playwright(url: str, timeout: int) -> str:
    """L34: Lento, pesado, mas renderiza JS completo."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            # Timeout do Playwright é em milissegundos
            await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            
            content = await page.content()
            if "Just a moment" in content:
                raise HTTPException(status_code=403, detail="Advanced WAF Blocked. JS Render evasion failed.")
            return content
        finally:
            await browser.close()

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
            async def fetch_strategy():
                if request.render_js:
                    return await _fetch_playwright(url_str, timeout_seconds)
                elif request.force_stealth:
                    return await _fetch_curlcffi(url_str, timeout_seconds)
                else:
                    return await _fetch_aiohttp(url_str, timeout_seconds)
                    
            html_content = await asyncio.wait_for(fetch_strategy(), timeout=timeout_seconds)
            
            config = {
                "archetype": request.archetype,
                "fidelity_threshold": request.fidelity_threshold,
                "allowed_domains": "*"
            }
            
            loop = asyncio.get_running_loop()
            clear_result = await loop.run_in_executor(
                process_pool, 
                run_dataclear_job,
                html_content, url_str, executor_used, config, "agentic-api-sync", "agentic-mission"
            )
            
            if clear_result.get("waf_blocked"):
                background_tasks.add_task(db.save_radar_log, customer_id, domain, "/fetch", 403)
                raise HTTPException(status_code=403, detail="Honeypot WAF Detectado pela Engenharia Reversa HTML.")
                
            background_tasks.add_task(db.save_radar_log, customer_id, domain, "/fetch", 200)
            entries = clear_result.get("dataset_entries", [])
            
            if not entries:
                markdown_body = ""
                semantic_chunks = []
            else:
                entry = entries[0]
                data = entry.get("data", {})
                markdown_body = data.get("markdown_body", "")
                semantic_chunks = data.get("semantic_chunks", [])
                
            processing_ms = int((time.time() - start_time) * 1000)
            
            final_response = FetchResponse(
                status="success",
                url=url_str,
                markdown_body=markdown_body,
                semantic_chunks=semantic_chunks,
                processing_ms=processing_ms,
                executor_used=executor_used
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
        # Recarga forçada do ENV para garantir que a chave esteja lá (Resiliência)
        from dotenv import load_dotenv
        load_dotenv()
        
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise HTTPException(status_code=500, detail="TAVILY_API_KEY missing in .env")
            
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
    
        async def fetch_safe(u):
            try:
                if request.force_stealth:
                    return {"url": u, "html": await _fetch_curlcffi(u, 15)}
                else:
                    return {"url": u, "html": await _fetch_aiohttp(u, 15)}
            except Exception as e:
                logger.error(f"Falha ao baixar {u}: {e}")
                return None
    
        fetch_results = await asyncio.gather(*(fetch_safe(u) for u in urls))
        valid_fetches = [f for f in fetch_results if f]
        
        if not valid_fetches:
            raise HTTPException(status_code=502, detail="As fontes encontradas estão inacessíveis no momento.")
    
        loop = asyncio.get_running_loop()
        markdown_parts = []
        urls_processed = []
        # Restaurando a régua de elite (0.6) conforme solicitado
        config = {"archetype": "blog", "fidelity_threshold": 0.6, "allowed_domains": "*"}
        
        for f in valid_fetches:
            try:
                res = await loop.run_in_executor(process_pool, run_dataclear_job, f["html"], f["url"], "L0", config, "radar", "mission")
                entries = res.get("dataset_entries", [])
                if entries:
                    md = entries[0].get("data", {}).get("markdown_body", "")
                    if md:
                        markdown_parts.append(f"# Fonte: {f['url']}\n{md}")
                        urls_processed.append(f['url'])
            except Exception as e:
                logger.error(f"Erro na limpeza da URL {f['url']}: {e}")
                continue
    
        if not markdown_parts:
            raise HTTPException(status_code=404, detail="O conteúdo encontrado não passou no filtro de qualidade (Fidelidade < 0.2).")
    
        return SearchFetchResponse(
            query=request.query,
            urls_processed=urls_processed,
            processing_ms=int((time.time() - start_time) * 1000),
            consolidated_markdown="\n\n---\n\n".join(markdown_parts)
        )
    except HTTPException:
        # Se for WAF, o cliente consome
        raise
    except Exception as e:
        logger.error(f"CRITICAL ERROR IN RADAR: {e}")
        # Estorno em caso de falha sistêmica
        await refund_credits(api_key, cost)
        raise HTTPException(status_code=500, detail=f"Erro Crítico no Radar: {str(e)}")
