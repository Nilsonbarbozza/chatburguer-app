import logging
from typing import Dict, Any
from bs4 import BeautifulSoup

from core.mq.worker_base import WorkerBase
from core.stages.dataclear import DataClearStage
from core.export.data_lake_writer import DataLakeWriter

logger = logging.getLogger("WorkerDataClear")

class WorkerDataClear(WorkerBase):
    """
    Consumidor Final. Tropa de Limpeza e Exportação.
    Puxa o HTML sujo coletado de qualquer fila (L0, L12, L34),
    Limpa NLP/PII e devolve em JSONL.
    """
    def __init__(self, redis_manager, worker_id: str):
        super().__init__(
            redis_manager=redis_manager,
            stream_name="stream:dataclear",
            group_name="workers_dataclear",
            worker_id=worker_id,
            concurrency=30 # Pode ser altissimo pois nao bate na rede web.
        )
        # O executor de PII (Redação Level 4 ativa)
        self.cleaner = DataClearStage(redact_pii=True, strict=True)
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
            # Recreia o contexto monolítico para a classe Legada funcionar sem alterar a interface
            soup = BeautifulSoup(html_content, 'lxml')
            context = {
                "soup": soup,
                "url": url,
                "executor_level": executor_level
            }
            
            # Geração Canônica e Limpeza
            processed_context = self.cleaner.process(context)
            
            # Ajuste para suportar múltiplos documentos explodidos de uma única URL
            final_entries = processed_context.get("dataset_entries", [])

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
