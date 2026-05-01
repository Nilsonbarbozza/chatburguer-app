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
    
    # 1. Fase: Radar (Integração Tavily)
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise HTTPException(status_code=500, detail="TAVILY_API_KEY not configured on server.")
        
    tavily_url = "https://api.tavily.com/search"
    tavily_payload = {
        "api_key": tavily_api_key,
        "query": request.query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": 2
    }
    
    urls_to_fetch = []
    async with aiohttp.ClientSession() as session:
        async with session.post(tavily_url, json=tavily_payload) as resp:
            if resp.status != 200:
                error_body = await resp.text()
                raise HTTPException(status_code=502, detail=f"Tavily Search Failed: {error_body}")
            data = await resp.json()
            urls_to_fetch = [result.get("url") for result in data.get("results", []) if result.get("url")]
            
    if not urls_to_fetch:
        raise HTTPException(status_code=404, detail="No relevant URLs found for the given query.")

    # 2. Fase: Ataque Simultâneo (Fetch Parallel)
    timeout_seconds = 15
    executor_used = "L12-curlcffi" if request.force_stealth else "L0-aiohttp"
    
    async def fetch_single_url(url_str: str) -> dict:
        try:
            if request.force_stealth:
                html = await asyncio.wait_for(_fetch_curlcffi(url_str, timeout_seconds), timeout=timeout_seconds)
            else:
                html = await asyncio.wait_for(_fetch_aiohttp(url_str, timeout_seconds), timeout=timeout_seconds)
            return {"url": url_str, "html": html, "success": True, "error": None}
        except Exception as e:
            return {"url": url_str, "html": None, "success": False, "error": str(e)}

    fetch_results = await asyncio.gather(*(fetch_single_url(u) for u in urls_to_fetch), return_exceptions=True)
    
    successful_fetches = [res for res in fetch_results if isinstance(res, dict) and res["success"]]
    failed_fetches = [res for res in fetch_results if isinstance(res, dict) and not res["success"]]
    
    if not successful_fetches:
        error_details = ", ".join([f"{f['url']}: {f['error']}" for f in failed_fetches])
        raise HTTPException(status_code=502, detail=f"All fetches failed. Details: {error_details}")

    # 3. Fase: DataClear (Pool Execution)
    loop = asyncio.get_running_loop()
    config = {
        "archetype": "article",
        "fidelity_threshold": request.fidelity_threshold,
        "allowed_domains": "*"
    }
    
    clear_tasks = []
    for fetch_res in successful_fetches:
        task = loop.run_in_executor(
            process_pool, 
            run_dataclear_job,
            fetch_res["html"], fetch_res["url"], executor_used, config, "search-and-fetch", "radar-mission"
        )
        clear_tasks.append((fetch_res["url"], task))
        
    markdown_parts = []
    urls_processed = []
    
    for url, task in clear_tasks:
        try:
            clear_result = await task
            entries = clear_result.get("dataset_entries", [])
            if entries:
                data = entries[0].get("data", {})
                md_body = data.get("markdown_body", "")
                title = data.get("title", url) # Try to get title, fallback to URL
                if md_body:
                    markdown_parts.append(f"# Fonte: {title}\n{md_body}")
                    urls_processed.append(url)
        except Exception as e:
            failed_fetches.append({"url": url, "error": f"DataClear failed: {str(e)}"})

    if not markdown_parts:
        raise HTTPException(status_code=500, detail="DataClear failed to extract content from all fetched URLs.")

    consolidated_markdown = "\n\n---\n\n".join(markdown_parts)
    processing_ms = int((time.time() - start_time) * 1000)
    
    error_message = None
    if failed_fetches:
        error_message = "Some sources failed: " + ", ".join([f"{f['url']} ({f['error']})" for f in failed_fetches])

    return SearchFetchResponse(
        query=request.query,
        urls_processed=urls_processed,
        processing_ms=processing_ms,
        consolidated_markdown=consolidated_markdown,
        error_message=error_message
    )

