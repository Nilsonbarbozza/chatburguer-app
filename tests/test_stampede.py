import asyncio
import aiohttp
import time
import json
import uuid

API_URL = "http://localhost:8000/api/v1/fetch"
HEADERS = {
    "X-API-Key": "sk-neuralsafety-d9e8014868694353",
    "Content-Type": "application/json"
}

async def fetch(session, url, render_js=False):
    payload = {
        "url": url,
        "render_js": render_js
    }
    start = time.time()
    try:
        async with session.post(API_URL, json=payload, headers=HEADERS) as response:
            resp_json = await response.json()
            elapsed = time.time() - start
            return {
                "status": response.status,
                "executor": resp_json.get("executor_used", "N/A"),
                "elapsed": elapsed
            }
    except Exception as e:
        return {"status": "error", "error": str(e), "elapsed": time.time() - start}

async def main():
    async with aiohttp.ClientSession() as session:
        print("=== Testando Cobrança Dinâmica (L0 vs L34) ===")
        # L0
        res0 = await fetch(session, "https://blog.dsacademy.com.br/10-bibliotecas-python-para-construir-aplicacoes-com-llms/", render_js=False)
        print(f"L0 Result: {res0}")
        
        # L34
        res34 = await fetch(session, "https://blog.dsacademy.com.br/10-bibliotecas-python-para-construir-aplicacoes-com-llms/", render_js=True)
        print(f"L34 Result: {res34}")
        
        print("\n=== Testando Escudo Anti-Manada (20 requisições simultâneas) ===")
        target_url = f"https://blog.dsacademy.com.br/10-bibliotecas-python-para-construir-aplicacoes-com-llms/?nocache={uuid.uuid4()}"
        
        # Dispara 20 requisições para a mesma URL
        tasks = [fetch(session, target_url, render_js=False) for _ in range(20)]
        
        start_stampede = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_stampede
        
        print(f"\nResultados do Stampede ({total_time:.2f}s totais):")
        winners = 0
        clones = 0
        errors = 0
        
        for r in results:
            if r["status"] == 200:
                if "cached" in r["executor"]:
                    clones += 1
                else:
                    winners += 1
            else:
                errors += 1
                print(r)
                
        print(f"Vencedores (Scraping Real): {winners}")
        print(f"Clones (Servidos do Cache): {clones}")
        print(f"Erros: {errors}")

if __name__ == "__main__":
    asyncio.run(main())
