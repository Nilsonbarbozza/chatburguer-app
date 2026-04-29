
import asyncio
import os
import logging
from core.mq.redis_manager import RedisManager
from core.mq.db_manager import DatabaseManager
from core.utils import setup_logging

setup_logging()
logger = logging.getLogger("ResgateCuradoria")

async def reprocess_mission(job_id: str):
    rm = RedisManager()
    db = DatabaseManager(dsn=os.getenv("POSTGRES_URL"))
    
    try:
        await db.connect()
        
        # 1. Busca a missão
        query_mission = "SELECT id FROM missions WHERE job_id = $1 ORDER BY created_at DESC LIMIT 1;"
        mission_id = await db.pool.fetchval(query_mission, job_id)
        
        if not mission_id:
            logger.error(f"❌ Missão {job_id} não encontrada no PostgreSQL.")
            return

        # 2. Busca todas as capturas desta missão
        query_captures = "SELECT id, url, raw_uri, executor_level FROM captures WHERE mission_id = $1;"
        rows = await db.pool.fetch(query_captures, mission_id)
        
        logger.info(f"📂 [RESGATE] Encontradas {len(rows)} capturas para a missão {job_id} ({mission_id})")

        # 3. Reinjeta no Stream de Curadoria
        count = 0
        for row in rows:
            payload = {
                "mission_id": str(mission_id),
                "job_id": job_id,
                "capture_id": str(row['id']),
                "url": row['url'],
                "raw_uri": row['raw_uri'],
                "executor_level": row['executor_level']
            }
            # Adiciona ao stream sem deduplicação (pois queremos forçar o reprocessamento)
            await rm.client.xadd("stream:dataclear", payload)
            count += 1
            
        logger.info(f"🚀 [SUCESSO] {count} capturas reinjetadas no stream:dataclear!")
        logger.info("Aguarde o processamento pelos workers DataClear.")

    except Exception as e:
        logger.error(f"💥 Falha no resgate: {e}")
    finally:
        await rm.close()
        await db.close()

if __name__ == "__main__":
    job_id = "missao_ia_375_ds_academy"
    asyncio.run(reprocess_mission(job_id))
