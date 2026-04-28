import asyncio
import logging
import concurrent.futures
from typing import Dict, Any
from core.mq.worker_base import WorkerBase
from core.stages.dataclear import run_dataclear_job
from core.export.data_lake_writer import DataLakeWriter

logger = logging.getLogger("WorkerDataClear")

class WorkerDataClear(WorkerBase):
    """
    Consumidor Final. Tropa de Limpeza e Exportação.
    Puxa o HTML sujo coletado de qualquer fila (L0, L12, L34),
    Limpa NLP/PII e devolve em JSONL.
    """
    def __init__(self, redis_manager, worker_id: str = None):
        super().__init__(
            redis_manager=redis_manager,
            stream_name="stream:dataclear",
            group_name="workers_dataclear",
            worker_id=worker_id,
            concurrency=30 # Pode ser altissimo pois nao bate na rede web.
        )
        # Pool de Processos para CPU-bound tasks (Parsing BeautifulSoup)
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=4)
        
        # Configurações do cleaner (serão passadas para o pool)
        self.redact_pii = True
        self.strict = True
        
        # Exportador
        self.writer = DataLakeWriter(output_dir="data/output")

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        html_content = data.get("html_content")
        executor_level = data.get("executor_level", "unknown")
        
        logger.info(f"🧹 [DataClear] Refinando URL extraída por {executor_level}...")
        
        if not html_content or not url:
            logger.error(f"[DataClear] Faltam propriedades fundamentais para {msg_id}")
            return False
            
        try:
            # Despacha o processamento pesado para o Pool de Processos (CPU-bound)
            # Isso impede que o BeautifulSoup trave o event loop assíncrono.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                run_dataclear_job,
                html_content,
                url,
                executor_level,
                self.redact_pii,
                self.strict
            )
            
            final_entries = result.get("dataset_entries", [])

            if final_entries:
                # Dispara a gravação pro Data Lake com o Job ID correto
                job_id = data.get("job_id", "batalhao_global")
                # O DataLakeWriter já suporta receber uma lista de documentos
                await self.writer.write_jsonl(job_id, final_entries)
                logger.info(f"💾 [DataClear] {len(final_entries)} registros salvos no Data Lake para {url}")
                return True
            else:
                logger.error(f"[DataClear] Dataset VAZIO para {url}")
                return False

        except Exception as e:
            logger.error(f"❌ Erro Crítico no Refino de Dados de {url}: {e}")
            return False
