import asyncio
import argparse
import sys
import logging
from typing import List
from core.mq.redis_manager import RedisManager
from core.utils import setup_logging

setup_logging()
logger = logging.getLogger("DespachanteIngest")

async def ingest_urls(file_path: str, job_id: str, respect_robots: bool, force_level: str = "auto"):
    """
    Ingestão massiva com deduplicação O(1) e Redis Pipeline.
    """
    rm = RedisManager(tenant_db_index=0)
    
    try:
        # 1. Leitura do arquivo
        with open(file_path, "r", encoding="utf-8") as f:
            # Filtra linhas vazias, comentários (#) e remove espaços
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

        if not urls:
            logger.warning(f"O arquivo {file_path} está vazio.")
            return

        logger.info(f"📂 Arquivo carregado: {len(urls)} URLs encontradas. Iniciando triagem...")

        # 2 e 3. Ingestão Atômica (Deduplicação + Enfileiramento em uma única operação Redis)
        # Protege contra Race Conditions em workers distribuídos.
        success_count = 0
        for url in urls:
            payload = {
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
            logger.warning(f"🛡️ Vacina Anti-Duplicidade: {duplicates_count} URLs já conhecidas foram ignoradas.")

        if success_count == 0:
            logger.info("✅ Nenhuma URL nova para processar. Missão encerrada.")
            return

        logger.info(f"🚀 MISSÃO DISPARADA! {success_count} URLs injetadas no funil de inteligência.")
        logger.info(f"Job ID: {job_id} | Robots: {respect_robots}")

    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {file_path}")
    except Exception as e:
        logger.error(f"Falha catastrófica na ingestão: {e}")
    finally:
        await rm.close()

def main():
    parser = argparse.ArgumentParser(description="Despachante de Missões do Batalhão — Ingestão Massiva")
    parser.add_argument("file", help="Caminho para o arquivo .txt com URLs (uma por linha)")
    parser.add_argument("--job", required=True, help="ID da Missão/Job (ex: cliente_alpha_v1)")
    parser.add_argument("--robots", type=str, default="true", help="Respeitar robots.txt? (true/false)")
    parser.add_argument("--force-level", type=str, default="auto", choices=["auto", "0", "12", "34"], help="Forçar nível de execução (0, 12, 34) ou auto")
    
    args = parser.parse_args()
    
    respect_robots = args.robots.lower() == "true"
    
    asyncio.run(ingest_urls(args.file, args.job, respect_robots, args.force_level))

if __name__ == "__main__":
    main()
