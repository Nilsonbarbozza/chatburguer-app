import asyncio
import json
import logging
import sys
import os

# Ajustar PYTHONPATH
sys.path.append(os.getcwd())

from core.stages.dataclear import run_dataclear_job
from agentic_api.routes import GOOGLEBOT_HEADERS, _fetch_aiohttp, _fetch_playwright

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger("Live-Test-OS014")

async def run_test(url):
    import time
    logger.info(f"\n🚀 TESTANDO URL: {url}")
    
    start_time = time.time()
    executor_used = "L0-aiohttp"
    tactic_used = "Traditional (BeautifulSoup)"
    config = {"archetype": "blog", "fidelity_threshold": 0.4} # Baixado para 0.4 para ser mais permissivo no teste
    
    try:
        # 1. Tentativa L0 (Googlebot)
        logger.info("📡 [L0] Tentando extração rápida com Googlebot Headers...")
        html_content = await _fetch_aiohttp(url, 15)
        
        # 2. Processamento (Injetando logs de debug para ver táticas)
        result = run_dataclear_job(html_content, url, executor_used, config)
        entries = result.get("dataset_entries", [])
        
        md = ""
        chunks = []
        if entries:
            data = entries[0].get("data", {})
            md = data.get("markdown_body", "")
            chunks = data.get("semantic_chunks", [])
            # Tenta descobrir qual tática foi usada via inspeção do resultado (ou logs se capturarmos)
            # Como o run_dataclear_job não retorna a tática, vamos inferir se houve extração rápida
            if len(md) > 500: tactic_used = "Zero-Latency (JSON-LD/Next.js)"
            
        # 3. Gatilho Fantasma
        if not chunks or len(md) < 300:
            logger.warning(f"⚠️ [GATILHO FANTASMA] Conteúdo insuficiente ({len(md)} chars). Escalando para L34 (Playwright)...")
            html_content = await _fetch_playwright(url, 60)
            executor_used = "L34-playwright-auto_fallback"
            tactic_used = "Ghost Trigger (Playwright Render)"
            
            result = run_dataclear_job(html_content, url, executor_used, config)
            entries = result.get("dataset_entries", [])
            if entries:
                data = entries[0].get("data", {})
                md = data.get("markdown_body", "")
                chunks = data.get("semantic_chunks", [])
        
        processing_ms = int((time.time() - start_time) * 1000)
        
        return {
            "url": url,
            "executor_used": executor_used,
            "tactic_used": tactic_used,
            "processing_ms": processing_ms,
            "success": len(chunks) > 0,
            "chunks_count": len(chunks),
            "content_length": len(md),
            "data": {
                "title": entries[0]["data"]["title"] if entries else "N/A",
                "markdown_preview": md[:500] + "...",
                "semantic_chunks": chunks
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro crítico no teste para {url}: {e}")
        return {"url": url, "success": False, "error": str(e)}

async def main():
    urls = [
        "https://blog.dsacademy.com.br/especialista-generalista-o-perfil-profissional-que-ganha-forca-na-era-da-ia/",
        "https://www.deeplearning.ai/blog/engineering-multi-agent-systems-a-path-from-prototype-to-production",
        "https://portaldatascience.com/blog/1",
        "https://exame.com/inteligencia-artificial/nadella-chama-conselho-que-demitiu-altman-de-cidade-de-amadores-em-julgamento/",
        "https://pautadupla.com.br/noticia/42387/ceo-da-blackrock-alerta-para-riscos-da-ia"
    ]
    all_results = []
    for url in urls:
        res = await run_test(url)
        all_results.append(res)
    
    # Salvar o JSON completo na raiz
    output_file = "extracao_completa_telemetria.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✅ EXTRAÇÃO COMPLETA! Relatório salvo em: {output_file}")
    print(json.dumps(all_results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
