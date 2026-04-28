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
        # Script LUA para garantir atomicidade entre Verificação e Inserção
        # Previne que múltiplos containers injetem a mesma URL se baterem ao mesmo tempo.
        lua_script = """
        local already_seen = redis.call('SISMEMBER', KEYS[1], ARGV[1])
        if already_seen == 0 then
            redis.call('SADD', KEYS[1], ARGV[1])
            redis.call('ZADD', KEYS[2], ARGV[2], ARGV[1])
            return 1
        end
        return 0
        """
        
        pipe = self.client.pipeline()
        for raw_url in urls:
            url = raw_url.lower().strip()
            # KEYS: [seen_set, priority_queue], ARGV: [url, score]
            pipe.eval(lua_script, 2, f"seen:{job_id}", "priority_queue", url, sla_score)
        
        results = await pipe.execute()
        return results

    async def atomic_ingest_to_stream(self, stream_name: str, url: str, payload: dict, dedup_set: str = "batalhao:global_dedup"):
        """
        Usa LUA para garantir que a URL só entra no Stream se não estiver no Set de dedup.
        Resolve o problema de 'Race Condition' em escala horizontal.
        """
        lua_script = """
        local already_seen = redis.call('SISMEMBER', KEYS[1], ARGV[1])
        if already_seen == 0 then
            redis.call('SADD', KEYS[1], ARGV[1])
            redis.call('XADD', KEYS[2], '*', 'url', ARGV[1], unpack(ARGV, 2))
            return 1
        end
        return 0
        """
        # Trasnforma payload dict em lista para o UNPACK do Lua [key1, val1, key2, val2...]
        flattened_payload = []
        for k, v in payload.items():
            if k != "url": # URL já é o ARGV[1]
                flattened_payload.extend([str(k), str(v)])
        
        result = await self.client.eval(lua_script, 2, dedup_set, stream_name, url, *flattened_payload)
        return bool(result)

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
