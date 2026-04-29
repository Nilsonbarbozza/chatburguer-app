
import asyncio
import logging
import concurrent.futures
import aiofiles
import os
import json
import hashlib
from typing import Dict, Any
from core.mq.worker_base import WorkerBase
from core.stages.dataclear import run_dataclear_job
from core.export.data_lake_writer import DataLakeWriter

logger = logging.getLogger("WorkerDataClear")

class WorkerDataClear(WorkerBase):
    """
    Consumidor Final (Curation Plane).
    Lê artefatos brutos do storage, aplica limpeza e gera datasets homologados.
    """
    def __init__(self, redis_manager, worker_id: str = None, db_manager=None, raw_store=None):
        super().__init__(
            redis_manager=redis_manager,
            stream_name="stream:dataclear",
            group_name="workers_dataclear",
            worker_id=worker_id,
            concurrency=30,
            db_manager=db_manager,
            raw_store=raw_store
        )
        # Pool de Processos para CPU-bound tasks
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=4)
        
        # Exportador
        self.writer = DataLakeWriter(base_path="data/curated")
        
        # Cache de Configurações de Missão
        self.mission_configs = {}

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        raw_uri = data.get("raw_uri")
        capture_id = data.get("capture_id")
        mission_id = data.get("mission_id", "default")
        executor_level = data.get("executor_level", "unknown")
        
        if not raw_uri or not url:
            logger.error(f"❌ [DataClear] Faltam referências para {msg_id}")
            return False
            
        logger.info(f"🧹 [DataClear] Refinando artefato: {raw_uri}")
        
        try:
            # 1. Carrega Conteúdo Bruto (Storage Access)
            html_content = await self.raw_store.load_content(raw_uri)
            
            # 1.1 DNA de Custo: Carrega metadados originais para preservar executor_level (Ação 2)
            meta_uri = raw_uri.replace(".html", ".meta.json").replace(".txt", ".meta.json").replace(".gz", ".meta.json")
            try:
                meta_content = await self.raw_store.load_content(meta_uri)
                meta_data = json.loads(meta_content)
                real_executor = meta_data.get("executor_level", executor_level)
            except:
                real_executor = executor_level

            # 2. Busca Configuração da Missão
            job_id = data.get("job_id", "batalhao_global")
            if job_id not in self.mission_configs:
                config = await self.rm.get_mission_config(job_id)
                self.mission_configs[job_id] = config or {}
            
            config = self.mission_configs[job_id]

            # 3. Processamento Pesado (CPU-bound)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                run_dataclear_job,
                html_content,
                url,
                real_executor,
                config,
                capture_id,
                mission_id
            )
            
            final_entries = result.get("dataset_entries", [])

            if final_entries:
                # 4. Exportação Homologada (Curated Store)
                file_path = await self.writer.write_jsonl(mission_id, final_entries, capture_id=capture_id)
                
                # 5. Fechamento do Elo no PostgreSQL (Ação 3)
                if self.db_manager and file_path:
                    run_id = await self.db_manager.register_curation_run(
                        capture_id=capture_id,
                        mission_id=mission_id,
                        metadata={"entries": len(final_entries), "executor": real_executor}
                    )
                    await self.db_manager.register_curated_artifact(
                        curation_run_id=run_id,
                        capture_id=capture_id,
                        mission_id=mission_id,
                        storage_path=file_path,
                        record_count=len(final_entries)
                    )
                
                logger.info(f"💾 [DataClear] {len(final_entries)} registros curados e catalogados para {url}")
                return True
            else:
                logger.warning(f"⚠️ [DataClear] Resultado vazio para {url}")
                return True # ACK - Processado mas sem output útil

        except Exception as e:
            logger.error(f"❌ Erro Crítico na Curadoria de {url}: {e}")
            return False
