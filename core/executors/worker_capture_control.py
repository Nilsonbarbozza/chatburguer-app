
import logging
from typing import Dict, Any
from core.mq.worker_base import WorkerBase

logger = logging.getLogger("CaptureControlWorker")

class CaptureControlWorker(WorkerBase):
    """
    Controlador de Tráfego de Captura.
    Ouve 'stream:captured_raw', registra no PostgreSQL e despacha para curadoria.
    """
    def __init__(self, redis_manager, db_manager, raw_store=None, worker_id: str = None):
        super().__init__(
            redis_manager=redis_manager,
            stream_name="stream:captured_raw",
            group_name="workers_capture_control",
            worker_id=worker_id,
            concurrency=20,
            db_manager=db_manager,
            raw_store=raw_store
        )

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        capture_id = data.get("capture_id")
        mission_id = data.get("mission_id")
        url = data.get("url")
        
        if not capture_id or not mission_id:
            logger.error(f"❌ Evento de captura malformado: {data}")
            return True # ACK para não travar a fila, mas logamos o erro

        logger.info(f"🚦 [CONTROLE] Registrando captura {capture_id} para URL: {url}")

        try:
            # 1. Registro no Catálogo (PostgreSQL) com o ID Original do Executor
            db_id = None
            if self.db_manager:
                db_id = await self.db_manager.register_capture(
                    mission_id=mission_id,
                    url=url,
                    executor_level=data.get("executor_level", "unknown"),
                    raw_uri=data.get("raw_uri"),
                    metadata_uri=data.get("metadata_uri"),
                    http_status=int(data.get("http_status", 200)),
                    content_hash=data.get("content_hash"),
                    capture_id=capture_id
                )

            # 2. Despacho para Curadoria (DataClear)
            curation_event = {
                "capture_id": db_id or capture_id,
                "mission_id": mission_id,
                "job_id": data.get("job_id"),
                "url": url,
                "raw_uri": data.get("raw_uri"),
                "metadata_uri": data.get("metadata_uri"),
                "rule_version": "v3_standard" # TODO: Tornar dinâmico via política
            }
            
            await self.rm.client.xadd("stream:dataclear", curation_event)
            
            logger.debug(f"✅ Captura {capture_id} catalogada e enviada para DataClear.")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao catalogar captura {capture_id}: {e}")
            return False
