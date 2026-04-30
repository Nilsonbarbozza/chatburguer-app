
import asyncio
import argparse
import sys
import os
# Adiciona a raiz do projeto ao path para localizar o 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mq.redis_manager import RedisManager
from core.mq.db_manager import DatabaseManager
from core.utils import setup_logging

setup_logging()
logger = logging.getLogger("DespachanteIngest")

async def ingest_urls(file_path: str, job_id: str, respect_robots: bool, 
                       force_level: str = "auto", mission_config: dict = None):
    """
    Ingestão Massiva Enterprise com Registro no Control Plane (PostgreSQL).
    """
    rm = RedisManager(tenant_db_index=0)
    db = DatabaseManager(dsn=os.getenv("POSTGRES_URL"))
    
    try:
        # 1. Registro no Control Plane (PostgreSQL)
        await db.connect()
        mission_id = await db.create_mission(job_id, metadata=mission_config)
        await db.register_policy(mission_id, mission_config)
        
        logger.info(f"🏛️ Missão Formalizada no Control Plane: {mission_id} (Job: {job_id})")

        # 2. Salva Configuração da Missão no Redis (Cache para Performance)
        if mission_config:
            mission_config["mission_id"] = str(mission_id)
            # Sanitização para o Redis (converte bool para string)
            sanitized_config = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in mission_config.items()}
            await rm.set_mission_config(job_id, sanitized_config)

        # 3. Leitura do arquivo
        with open(file_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

        if not urls:
            logger.warning(f"O arquivo {file_path} está vazio.")
            return

        logger.info(f"📂 Arquivo carregado: {len(urls)} URLs. Iniciando triagem...")

        # 4. Ingestão Atômica com Rastreabilidade
        success_count = 0
        for url in urls:
            payload = {
                "mission_id": mission_id,
                "job_id": job_id,
                "respect_robots": str(respect_robots).lower(),
                "force_level": force_level,
                "ingested_at": str(asyncio.get_event_loop().time())
            }
            # O RedisManager cuida da atomicidade e deduplicação via Lua
            is_new = await rm.atomic_ingest_to_stream("stream:ingestion", url, payload)
            if is_new:
                success_count += 1
        
        duplicates_count = len(urls) - success_count
        if duplicates_count > 0:
            logger.warning(f"🛡️ Vacina Anti-Duplicidade: {duplicates_count} URLs ignoradas.")

        logger.info(f"🚀 MISSÃO DISPARADA! {success_count} URLs injetadas.")
        logger.info(f"Mission ID: {mission_id} | Job ID: {job_id}")

    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {file_path}")
    except Exception as e:
        logger.error(f"Falha catastrófica na ingestão: {e}")
    finally:
        await rm.close()
        await db.close()

def main():
    parser = argparse.ArgumentParser(description="Despachante de Missões - Grande Desacoplamento")
    parser.add_argument("file", help="Arquivo .txt com URLs")
    parser.add_argument("--job", required=True, help="ID da Missão/Job")
    parser.add_argument("--robots", type=str, default="true", help="Respeitar robots.txt?")
    parser.add_argument("--force-level", type=str, default="auto", choices=["auto", "0", "12", "34"], help="Forçar nível")
    
    parser.add_argument("--archetype", type=str, default="blog", help="Arquétipo")
    parser.add_argument("--threshold", type=float, default=0.6, help="Fidelity Threshold")
    parser.add_argument("--allowed-domains", type=str, default="*", help="Domínios permitidos")

    args = parser.parse_args()
    respect_robots = args.robots.lower() == "true"

    mission_config = {
        "archetype": args.archetype,
        "fidelity_threshold": args.threshold,
        "allowed_domains": args.allowed_domains,
        "job_id": args.job,
        "respect_robots": respect_robots,
        "force_level": args.force_level
    }
    
    asyncio.run(ingest_urls(args.file, args.job, respect_robots, args.force_level, mission_config))

if __name__ == "__main__":
    main()
