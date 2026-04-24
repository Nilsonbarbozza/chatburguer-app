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

        # 2. Deduplicação Massiva (Fase 1: Verificar quem é novo)
        # Usamos SADD: retorna 1 se foi adicionado (novo), 0 se já existia
        pipe = rm.client.pipeline()
        for url in urls:
            pipe.sadd("batalhao:global_dedup", url)
        
        dedup_results = await pipe.execute()
        
        new_urls = [url for url, is_new in zip(urls, dedup_results) if is_new]
        duplicates_count = len(urls) - len(new_urls)

        if duplicates_count > 0:
            logger.warning(f"🛡️ Vacina Anti-Duplicidade: {duplicates_count} URLs descartadas por já terem sido processadas anteriormente.")

        if not new_urls:
            logger.info("✅ Nenhuma URL nova para processar. Missão encerrada.")
            return

        # 3. Ingestão no Pipeline (Fase 2: XADD em massa)
        pipe = rm.client.pipeline()
        for url in new_urls:
            payload = {
                "url": url,
                "job_id": job_id,
                "respect_robots": str(respect_robots).lower(),
                "force_level": force_level,
                "ingested_at": str(asyncio.get_event_loop().time())
            }
            pipe.xadd("stream:ingestion", payload)
        
        await pipe.execute()
        
        logger.info(f"🚀 MISSÃO DISPARADA! {len(new_urls)} URLs injetadas no funil de inteligência.")
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
