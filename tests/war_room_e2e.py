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

# Mock do Pipeline do Redis (deve ser síncrono o retorno do pipeline(), mas o execute() é asíncrono)
class MockPipeline:
    def __init__(self):
        self.results = [None, None, 1, True] 
    def zremrangebyscore(self, *args, **kwargs): return self
    def zadd(self, *args, **kwargs): return self
    def zcard(self, *args, **kwargs): return self
    def expire(self, *args, **kwargs): return self
    def hincrby(self, *args, **kwargs): return self
    async def execute(self): return self.results

# O pipeline() no redis-py async NÃO é um coroutine, é um factory síncrono.
mock_redis.pipeline = MagicMock(return_value=MockPipeline())

class MockRedisManager:
    def __init__(self, tenant_db_index=0):
        self.client = mock_redis
    async def close(self): pass

class MockDatabaseManager:
    def __init__(self):
        self.pool = MagicMock()
    async def connect(self): pass
    async def save_radar_log(self, *args): pass
    async def close(self): pass

# Patchear antes de importar o app
with patch('core.mq.redis_manager.RedisManager', MockRedisManager), \
     patch('core.database.db', MockDatabaseManager()):
    
    import core.executors.waterfall as waterfall
    print(f"DEBUG: Loading waterfall from: {waterfall.__file__}")
    
    from agentic_api.main import app
    from agentic_api.schemas import Archetype

client = TestClient(app)

log_capture = []
class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        if "[METRICS]" in msg or "[AUCTION-GRID]" in msg or "[WAF-DETECT]" in msg:
            log_capture.append(msg)

logger = logging.getLogger("html_processor")
logger.addHandler(LogCaptureHandler())
logger.setLevel(logging.INFO)

def run_war_room():
    print("\n" + "="*60)
    print("OPERACO WAR ROOM -- RELATORIO DE HOMOLOGACAO E2E")
    print("="*60)

    # Setup Redis Mocks
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

    # --- PILAR 1: MULTI-ARQUÉTIPO ---
    print("\nPILLAR 1: BATERIA MULTI-ARQUETIPO")
    
    test_cases = [
        ("ARTICLE", "https://exame.com/invest/mercados/bolsa-hoje-ao-vivo/", Archetype.ARTICLE),
        ("AUCTION", "https://www.megaleiloes.com.br/imoveis", Archetype.AUCTION_GRID),
        ("HUB", "https://www.infomoney.com.br/category/mercados/", Archetype.HUB)
    ]

    for label, url, arch in test_cases:
        print(f"Testing {label} extraction for: {url}...")
        t0 = time.time()
        
        # Reseta o cache de erro para cada teste
        mock_redis.get.return_value = None
        
        response = client.post("/api/v1/fetch", json={
            "url": url,
            "archetype": arch,
            "force_stealth": True,
            "fidelity_threshold": 0.3
        }, headers=headers)
        
        elapsed = time.time() - t0
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] {label} Sucesso: {elapsed:.2f}s | Chunks: {len(data.get('semantic_chunks', []))} | Hub Items: {len(data.get('hub_items', []))}")
        else:
            print(f"[ERROR] {label} Falhou: {response.status_code} | {response.text}")

    # --- PILAR 2: INFRAESTRUTURA (REDIS CACHE) ---
    print("\nPILLAR 2: MALHA DE INFRAESTRUTURA (REDIS)")
    
    url_test = "https://leilao.com/grid"
    mock_redis.get.return_value = json.dumps({
        "status": "success",
        "url": url_test,
        "markdown_body": "Cached content",
        "semantic_chunks": [],
        "hub_items": [{"id_lote": "CACHED123"}],
        "processing_ms": 5,
        "executor_used": "L0-aiohttp (cached)"
    })
    
    print(f"Testing Cache Hit for: {url_test}...")
    response = client.post("/api/v1/fetch", json={"url": url_test, "archetype": Archetype.AUCTION_GRID}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if "(cached)" in data["executor_used"]:
            print(f"[OK] REDIS CACHE HIT: Confirmado em {data['processing_ms']}ms")
        else:
            print(f"[ERROR] REDIS CACHE HIT: Falhou (Executou pipeline real)")
    else:
        print(f"[ERROR] REDIS CACHE TEST: Falhou {response.status_code}")

    # --- PILAR 3: ENDPOINTS (SEARCH & FETCH) ---
    print("\nPILLAR 3: TESTE DE ENDPOINTS (SEARCH & FETCH)")
    
    # Mock do Tavily via patch no routes.py se necessário, ou apenas dispara
    print("Testing /search_and_fetch for 'leilao trator sp'...")
    response = client.post("/api/v1/search_and_fetch", json={
        "query": "leilao trator sp",
        "fidelity_threshold": 0.3
    }, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] SEARCH & FETCH Sucesso: {len(data['results'])} resultados encontrados.")
    else:
        print(f"[ERROR] SEARCH & FETCH Falhou: {response.status_code}")

    # --- PILAR 4: TELEMETRIA ---
    print("\nPILLAR 4: TELEMETRIA E LOGS")
    metrics_count = sum(1 for log in log_capture if "[METRICS]" in log)
    if metrics_count > 0:
        print(f"[OK] TELEMETRIA: {metrics_count} entradas de [METRICS] capturadas.")
        for log in log_capture[:3]:
            print(f"   > {log}")
    else:
        print("[ERROR] TELEMETRIA: Nenhum log de [METRICS] encontrado.")

    print("\n" + "="*60)
    print("FINISH OPERACAO WAR ROOM CONCLUIDA")
    print("="*60)

if __name__ == "__main__":
    run_war_room()
