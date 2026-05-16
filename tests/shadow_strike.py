import sys
import os
import json
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.getcwd())

# === INFRASTRUCTURE MOCKS ===
mock_redis = AsyncMock()

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

def shadow_strike():
    print("\n" + "=" * 70)
    print("OPERACAO SHADOW STRIKE - BATISMO DE FOGO L12 HARDENED")
    print("=" * 70)

    mock_redis.hgetall.return_value = {
        "status": "active", "quota_limit": "1000",
        "quota_used": "0", "client_name": "ShadowStrike_CMD"
    }
    mock_redis.get.return_value = None
    mock_redis.eval.return_value = 900
    headers = {"X-API-Key": "shadow_strike_key"}

    ts = int(time.time())
    targets = [
        ("mega_proxy", f"https://www.megaleiloes.com.br/imoveis/sp/sao-paulo?t={ts}", Archetype.AUCTION_GRID),
    ]

    for label, url, arch in targets:
        print(f"\n--- ALVO [{label}]: {url} ---")
        mock_redis.get.return_value = None
        t0 = time.time()

        try:
            response = client.post("/api/v1/fetch", json={
                "url": url,
                "archetype": arch,
                "force_stealth": False,  # Cascata L0 -> L12 -> L34
                "fidelity_threshold": 0.1
            }, headers=headers)

            elapsed = time.time() - t0
            print(f"HTTP Status: {response.status_code} ({elapsed:.1f}s)")

            if response.status_code == 200:
                result = response.json()
                filename = f"shadow_strike_{label}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                hub_items = result.get('hub_items') or []
                chunks = result.get('semantic_chunks') or []
                executor = result.get('executor_used', 'N/A')

                print(f"Executor: {executor}")
                print(f"Hub Items: {len(hub_items)}")
                print(f"Chunks:    {len(chunks)}")
                print(f"Arquivo:   {filename}")

                if hub_items:
                    item = hub_items[0]
                    print(f"\n--- SAMPLE ITEM (1/{len(hub_items)}) ---")
                    print(json.dumps(item, indent=2, ensure_ascii=False))
            else:
                print(f"BLOCKED: {response.text[:300]}")
        except Exception as e:
            print(f"CRITICAL: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("SHADOW STRIKE CONCLUIDA")
    print("=" * 70)

if __name__ == "__main__":
    shadow_strike()
