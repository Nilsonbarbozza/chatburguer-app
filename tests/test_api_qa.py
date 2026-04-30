import asyncio
import aiohttp
import time

API_URL = "http://localhost:8000"
VALID_KEY = "sk-neuralsafety-enterprise-v1"
INVALID_KEY = "sk-fake-key"

async def test_pulse():
    print("\n--- TESTE 1: PULSO (Healthcheck) ---")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/health") as response:
            status = response.status
            data = await response.json()
            print(f"Status: {status} | Resposta: {data}")
            if status == 200:
                print("[SUCESSO] Teste de Pulso Aprovado")
            else:
                print("[FALHA] Falha no Teste de Pulso")

async def test_shield():
    print("\n--- TESTE 2: ESCUDO (Auth 401) ---")
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": INVALID_KEY}
        payload = {"url": "https://example.com"}
        async with session.post(f"{API_URL}/api/v1/fetch", headers=headers, json=payload) as response:
            status = response.status
            data = await response.json()
            print(f"Status: {status} | Resposta: {data}")
            if status == 401:
                print("[SUCESSO] Teste de Escudo Aprovado (Ameaca Barrada)")
            else:
                print("[FALHA] Falha no Teste de Escudo")

async def test_clean_load():
    print("\n--- TESTE 3: CARGA LIMPA (Sub-3s, 200 OK) ---")
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": VALID_KEY}
        payload = {
            "url": "https://example.com",
            "force_stealth": False,
            "render_js": False,
            "fidelity_threshold": 0.0 # Baixo para garantir que nao descarte a pagina pequena de exemplo
        }
        start = time.time()
        async with session.post(f"{API_URL}/api/v1/fetch", headers=headers, json=payload) as response:
            elapsed = time.time() - start
            status = response.status
            data = await response.json()
            print(f"Status: {status} | Tempo: {elapsed:.2f}s")
            if status == 200 and elapsed < 3.0:
                print("[SUCESSO] Teste de Carga Limpa Aprovado")
                print(f"Executor: {data.get('executor_used')} | Markdown Preview: {data.get('markdown_body')[:60]}...")
            else:
                print(f"[FALHA] Falha no Teste de Carga Limpa. Erro: {data}")

async def test_stress():
    print("\n--- TESTE 4: ESTRESSE (Rate Limit 429) ---")
    # Disparar 65 requests concorrentes (o limite e 60)
    async def make_request(session, idx):
        headers = {"X-API-Key": VALID_KEY}
        payload = {"url": "https://example.com", "fidelity_threshold": 0.0}
        async with session.post(f"{API_URL}/api/v1/fetch", headers=headers, json=payload) as response:
            return response.status
            
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, i) for i in range(65)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        status_counts = {}
        for r in results:
            status_counts[r] = status_counts.get(r, 0) + 1
            
        print(f"Distribuicao de Status (65 requests disparados): {status_counts}")
        if 429 in status_counts:
            print("[SUCESSO] Teste de Estresse Aprovado (Bloqueio 429 acionado)")
        else:
            print("[FALHA] Falha no Teste de Estresse (Nenhum bloqueio ou todos falharam)")

async def main():
    await test_pulse()
    await test_shield()
    await test_clean_load()
    await test_stress()

if __name__ == "__main__":
    asyncio.run(main())
