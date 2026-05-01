import time
import asyncio
import aiohttp
from curl_cffi.requests import AsyncSession as CurlCffiSession
from fastapi import APIRouter, Depends, HTTPException
from concurrent.futures import ProcessPoolExecutor

import os
from agentic_api.schemas import FetchRequest, FetchResponse, SearchFetchRequest, SearchFetchResponse
from agentic_api.auth import validate_api_key_and_rate_limit
from core.stages.dataclear import run_dataclear_job

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
    customer_id: str = Depends(validate_api_key_and_rate_limit)
):
    start_time = time.time()
    url_str = str(request.url)
    
    # 1. Regra de Negócio: Definição de Timeout e Armamento
    timeout_seconds = 45 if request.render_js else 15
    executor_used = "L0-aiohttp"
    
    try:
        html_content = ""
        
        async def fetch_strategy():
            nonlocal executor_used
            if request.render_js:
                executor_used = "L34-playwright"
                return await _fetch_playwright(url_str, timeout_seconds)
            elif request.force_stealth:
                executor_used = "L12-curlcffi"
                return await _fetch_curlcffi(url_str, timeout_seconds)
            else:
                return await _fetch_aiohttp(url_str, timeout_seconds)
                
        # Proteção global com asyncio.wait_for
        html_content = await asyncio.wait_for(fetch_strategy(), timeout=timeout_seconds)
        
        # 2. Despacho de Processamento Pesado (CPU-Bound)
        # Passa o html_content pro ProcessPoolExecutor. A thread principal fica livre.
        config = {
            "archetype": request.archetype,
            "fidelity_threshold": request.fidelity_threshold,
            "allowed_domains": "*" # API não restringe domínio
        }
        
        loop = asyncio.get_running_loop()
        clear_result = await loop.run_in_executor(
            process_pool, 
            run_dataclear_job,
            html_content, url_str, executor_used, config, "agentic-api-sync", "agentic-mission"
        )
        
        if clear_result.get("waf_blocked"):
            raise HTTPException(status_code=403, detail="Honeypot WAF Detectado pela Engenharia Reversa HTML.")
            
        entries = clear_result.get("dataset_entries", [])
        
        # Se a página foi purificada abaixo do fidelity_threshold, volta vazio
        if not entries:
            markdown_body = ""
            semantic_chunks = []
        else:
            entry = entries[0]
            data = entry.get("data", {})
            markdown_body = data.get("markdown_body", "")
            semantic_chunks = data.get("semantic_chunks", [])
            
        processing_ms = int((time.time() - start_time) * 1000)
        
        return FetchResponse(
            status="success",
            url=url_str,
            markdown_body=markdown_body,
            semantic_chunks=semantic_chunks,
            processing_ms=processing_ms,
            executor_used=executor_used
        )
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, 
            detail=f"Gateway Timeout: Extraction took longer than {timeout_seconds}s. Try increasing timeout with render_js if needed."
        )
    except HTTPException:
        raise # Repassa as exceções de bloco e limite que já estruturamos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Extraction Error: {str(e)}")

@router.post("/search_and_fetch", response_model=SearchFetchResponse)
async def search_and_fetch(
    request: SearchFetchRequest,
    customer_id: str = Depends(validate_api_key_and_rate_limit)
):
    start_time = time.time()
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise HTTPException(status_code=500, detail="TAVILY_API_KEY not configured.")
        
    # 1. Radar (Tavily)
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.tavily.com/search", json={"api_key": tavily_api_key, "query": request.query, "max_results": 2}) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=502, detail="Tavily Search Failed")
            data = await resp.json()
            urls = [r.get("url") for r in data.get("results", []) if r.get("url")]
            
    if not urls:
        raise HTTPException(status_code=404, detail="No relevant URLs found.")

    # 2. Fetch Paralelo usando seus helpers originais
    async def fetch_wrapper(u):
        try:
            if request.force_stealth:
                return {"url": u, "html": await _fetch_curlcffi(u, 15)}
            else:
                return {"url": u, "html": await _fetch_aiohttp(u, 15)}
        except:
            return None

    fetch_results = await asyncio.gather(*(fetch_wrapper(u) for u in urls))
    valid_fetches = [f for f in fetch_results if f]
    
    if not valid_fetches:
        raise HTTPException(status_code=502, detail="All fetches failed.")

    # 3. DataClear em Pool
    loop = asyncio.get_running_loop()
    markdown_parts = []
    urls_processed = []
    
    # Usando o arquétipo 'blog' que é o padrão de performance do seu sistema
    config = {"archetype": "blog", "fidelity_threshold": request.fidelity_threshold, "allowed_domains": "*"}
    
    for f in valid_fetches:
        try:
            res = await loop.run_in_executor(process_pool, run_dataclear_job, f["html"], f["url"], "L0", config, "radar", "mission")
            entries = res.get("dataset_entries", [])
            if entries:
                md = entries[0].get("data", {}).get("markdown_body", "")
                if md:
                    markdown_parts.append(f"# Fonte: {f['url']}\n{md}")
                    urls_processed.append(f['url'])
        except:
            continue

    if not markdown_parts:
        raise HTTPException(status_code=500, detail="Extraction failed.")

    return SearchFetchResponse(
        query=request.query,
        urls_processed=urls_processed,
        processing_ms=int((time.time() - start_time) * 1000),
        consolidated_markdown="\n\n---\n\n".join(markdown_parts)
    )

