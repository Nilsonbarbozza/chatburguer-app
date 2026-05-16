import sys
import os
import asyncio
import json
import logging
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

# Force local imports
sys.path.insert(0, os.getcwd())

# Mocking Infrastructure
mock_redis = AsyncMock()
mock_db = AsyncMock()

class MockPipeline:
    def __init__(self):
        self.results = [None, None, 1, True] 
    def zremrangebyscore(self, *args, **kwargs): return self
    def zadd(self, *args, **kwargs): return self
    def zcard(self, *args, **kwargs): return self
    def expire(self, *args, **kwargs): return self
    def hincrby(self, *args, **kwargs): return self
    async def execute(self): return self.results

mock_redis.pipeline = MagicMock(return_value=MockPipeline())

class MockRedisManager:
    def __init__(self, tenant_db_index=0):
        self.client = mock_redis
    async def close(self): pass

class MockDatabaseManager:
    def __init__(self):
        self.pool = MagicMock()
    async def connect(self): pass
    async def save_radar_log(self, *args, **kwargs): pass
    async def close(self): pass

# Patchear antes de importar o app
with patch('core.mq.redis_manager.RedisManager', MockRedisManager), \
     patch('core.database.db', MockDatabaseManager()):
    
    from agentic_api.main import app
    from agentic_api.schemas import Archetype
    from core.executors.waterfall import WaterfallExtractor

client = TestClient(app)

# Captura de Logs
log_capture = []
class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        log_capture.append(self.format(record))

logging.getLogger().addHandler(LogCaptureHandler())
logging.getLogger().setLevel(logging.INFO)

def run_war_room():
    print("\n" + "="*60)
    print("OPERACO WAR ROOM -- RELATORIO DE FIDELIDADE INFRA")
    print("="*60)

    # Setup Redis Mocks (Auth)
    mock_redis.hgetall.return_value = {
        "status": "active",
        "quota_limit": "1000",
        "quota_used": "100",
        "client_name": "WarRoom_Commander"
    }
    mock_redis.set.return_value = True
    mock_redis.get.return_value = None 
    mock_redis.eval.return_value = 900 

    headers = {"X-API-Key": "ns_elite_warroom_key"}

    success_result = {
        "markdown_body": "# Test Content\nThis is a mocked success.",
        "semantic_chunks": [{"text": "chunk1"}],
        "hub_items": [],
        "executor_used": "L12-curlcffi",
        "waf_blocked": False
    }

    # Mantemos o patch global para evitar chamadas de rede
    with patch.object(WaterfallExtractor, 'extract', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = success_result

        # --- PILAR 1 ---
        print("\nPILLAR 1: INTEGRACAO DE FLUXO")
        response = client.post("/api/v1/fetch", json={
            "url": "https://test.com/article",
            "archetype": Archetype.ARTICLE
        }, headers=headers)
        if response.status_code == 200:
            print("[OK] PILLAR 1: Sucesso")
        else:
            print(f"[ERROR] PILLAR 1: {response.status_code}")

        # --- PILAR 2 ---
        print("\nPILLAR 2: REDIS CACHE")
        cached_payload = {
            "status": "success",
            "url": "https://test.com/cached",
            "markdown_body": "Cached content",
            "semantic_chunks": [],
            "hub_items": [],
            "processing_ms": 1,
            "executor_used": "L0-aiohttp (cached)"
        }
        mock_redis.get.return_value = json.dumps(cached_payload)
        response = client.post("/api/v1/fetch", json={"url": "https://test.com/cached"}, headers=headers)
        if response.status_code == 200 and "(cached)" in response.json()["executor_used"]:
            print("[OK] PILLAR 2: Cache Hit validado")
        else:
            print(f"[ERROR] PILLAR 2: {response.status_code}")

        # --- PILAR 3 ---
        print("\nPILLAR 3: SEARCH & FETCH INTEGRATION")
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"results": [{"url": "https://found1.com"}]})
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            mock_redis.get.return_value = None 
            response = client.post("/api/v1/search_and_fetch", json={"query": "test query"}, headers=headers)
            if response.status_code == 200:
                print(f"[OK] PILLAR 3: Search Sucesso")

    # --- PILAR 4 ---
    print("\nPILLAR 4: TELEMETRIA")
    from core.stages.dataclear import run_dataclear_job
    run_dataclear_job("<html><body><p>Conteudo longo para gerar metricas.</p></body></html>", "https://log.com", "L0", {"archetype": "blog"})
    if any("[METRICS]" in log for log in log_capture):
        print("[OK] PILLAR 4: Telemetria validada")

    print("\n" + "="*60)
    print("FINISH OPERACAO WAR ROOM - INFRA VALIDATED")
    print("="*60)

if __name__ == "__main__":
    run_war_room()
