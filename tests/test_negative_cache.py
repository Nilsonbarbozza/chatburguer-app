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

async def fetch(session, url):
    payload = {"url": url, "render_js": False}
    start = time.time()
    try:
        async with session.post(API_URL, json=payload, headers=HEADERS) as response:
            resp_json = await response.json()
            return {
                "status": response.status,
                "detail": resp_json.get("detail", ""),
                "elapsed": time.time() - start
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def main():
    async with aiohttp.ClientSession() as session:
        # Gerar uma URL que vai falhar (Porta fechada causa Exception)
        target_url = f"http://localhost:9999/fail_{uuid.uuid4()}"
        
        print(f"=== Testando Negative Caching (Alvo: {target_url}) ===")
        
        # 1. Disparar o Vencedor e os Clones simultaneamente
        # O Vencedor vai falhar ao tentar conectar no localhost:9999
        tasks = [fetch(session, target_url) for _ in range(5)]
        
        print("Disparando 5 requisições (1 Vencedor + 4 Clones)...")
        results = await asyncio.gather(*tasks)
        
        print("\nResultados:")
        for i, r in enumerate(results):
            type_req = "Vencedor" if i == 0 else "Clone"
            print(f"Request {i+1} ({type_req}): Status {r['status']} | Detail: {r['detail']}")

        # 2. Verificar se uma nova requisição IMEDIATA (mesmo após o erro) pega o Cache Negativo
        print("\nVerificando se a proteção de 60s está ativa (Instantânea)...")
        instant_res = await fetch(session, target_url)
        print(f"Nova Request: Status {instant_res['status']} | Detail: {instant_res['detail']}")
        
        if "[NEGATIVE CACHE]" in str(instant_res['detail']):
            print("\nSUCESSO: Escudo Anti-Manada interceptou a missão suicida!")
        else:
            print("\nFALHA: O escudo nao foi ativado corretamente.")

if __name__ == "__main__":
    asyncio.run(main())
