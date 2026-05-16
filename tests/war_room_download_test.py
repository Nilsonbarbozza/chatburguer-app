import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

# Force local imports
sys.path.insert(0, os.getcwd())

# Mocking Infrastructure
mock_redis = AsyncMock()
mock_db = AsyncMock()

class MockPipeline:
    def __init__(self): self.results = [None, None, 1, True] 
    def zremrangebyscore(self, *args, **kwargs): return self
    def zadd(self, *args, **kwargs): return self
    def zcard(self, *args, **kwargs): return self
    def expire(self, *args, **kwargs): return self
    def hincrby(self, *args, **kwargs): return self
    async def execute(self): return self.results

mock_redis.pipeline = MagicMock(return_value=MockPipeline())

class MockRedisManager:
    def __init__(self, tenant_db_index=0): self.client = mock_redis
    async def close(self): pass

class MockDatabaseManager:
    def __init__(self): self.pool = MagicMock()
    async def connect(self): pass
    async def save_radar_log(self, *args, **kwargs): pass
    async def close(self): pass

with patch('core.mq.redis_manager.RedisManager', MockRedisManager), \
     patch('core.database.db', MockDatabaseManager()):
    
    from agentic_api.main import app
    from agentic_api.schemas import Archetype

client = TestClient(app)

def run_fogo_real_v2():
    print("\n" + "!"*80)
    print("OPERACAO SNIPER V7: FOGO REAL (HARDENED)")
    print("!"*80)
    
    mock_redis.hgetall.return_value = {
        "status": "active",
        "quota_limit": "1000",
        "quota_used": "0",
        "client_name": "Sniper_V7_Commander"
    }
    mock_redis.get.return_value = None 
    mock_redis.eval.return_value = 900 
    headers = {"X-API-Key": "sniper_v7_key"}

    # Focaremos no AUCTION_GRID que falhou anteriormente
    targets = [
        ("auction_sp", "https://www.megaleiloes.com.br/imoveis/sp/sao-paulo?v=sniper7", Archetype.AUCTION_GRID)
    ]

    for label, url, arch in targets:
        print(f"\n--- ATACANDO ALVO [{label}]: {url} ---")
        mock_redis.get.return_value = None 
        
        try:
            response = client.post("/api/v1/fetch", json={
                "url": url,
                "archetype": arch,
                "force_stealth": False, # Testa a cascata L0 -> L34
                "fidelity_threshold": 0.1 # Threshold baixo para depuração
            }, headers=headers)

            if response.status_code == 200:
                result = response.json()
                filename = f"sniper_v7_{label}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                hub_items = result.get('hub_items') or []
                chunks = result.get('semantic_chunks') or []
                
                print(f"OK: Extração Concluída!")
                print(f"Executor Final: {result['executor_used']}")
                print(f"Data Found: {len(hub_items)} Hub Items / {len(chunks)} Chunks")
                
                if hub_items:
                    print(f"Sample Item: {json.dumps(hub_items[0], indent=2, ensure_ascii=False)}")
                
                print(f"Arquivo salvo: {filename}")
            else:
                print(f"ERRO [{label}]: {response.status_code} | {response.text}")
        except Exception as e:
            print(f"CRITICAL ERROR [{label}]: {e}")

    print("\n" + "!"*80)
    print("OPERACAO SNIPER V7 CONCLUIDA")
    print("!"*80)

if __name__ == "__main__":
    run_fogo_real_v2()
