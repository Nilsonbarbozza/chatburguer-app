import os
import redis.asyncio as redis_async
import redis.exceptions
import logging
from typing import List

logger = logging.getLogger("RedisManager")

# Configuração Padrão do Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class RedisManager:
    """
    Gerenciador unificado de conexão Redis.
    Implementa o Model B (Multi-tenancy via `db` isolation).
    """

    def __init__(self, tenant_db_index: int = 0):
        """
        Inicializa a conexão Redis para um cliente (tenant) específico.
        :param tenant_db_index: O índice do banco de dados Redis.
                                0 = Main/Shared
                                1..N = Tenants Isolados
        """
        self.db_index = tenant_db_index
        self.url = f"{REDIS_URL}/{self.db_index}"
        self.client = redis_async.from_url(self.url, decode_responses=True)
        
    async def ingest_urls(self, urls: List[str], job_id: str, sla_score: float):
        """
        Ingere URLs no broker usando pipeline para performance.
        Verifica deduplicação e define a prioridade baseada no SLA.
        """
        pipe = self.client.pipeline()
        for raw_url in urls:
            url = raw_url.lower().strip()
            # Usando O(1) SET lookup para deduplicação
            already_seen = await self.client.sismember(f"seen:{job_id}", url)
            
            if not already_seen:
                pipe.sadd(f"seen:{job_id}", url)
                # Adiciona na Priority Queue global deste Tenant
                pipe.zadd("priority_queue", {url: sla_score})
        
        results = await pipe.execute()
        return results

    async def init_streams(self, streams: List[str], group_name: str = "workers"):
        """
        Garante que os streams necessários existam para que os XREADGROUPs não crashem.
        """
        for stream in streams:
            try:
                # O comando XGROUP CREATE falha se o stream já existir ou pacote falhar
                # Usamo MKSTREAM para forçar a criacao se nao existir
                await self.client.xgroup_create(stream, group_name, id="0", mkstream=True)
                logger.info(f"Stream '{stream}' e consumer group '{group_name}' inicializados.")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    pass # O consumer group ja existe
                else:
                    logger.error(f"Erro ao criar stream {stream}: {e}")

    async def close(self):
        await self.client.aclose()
