import logging
import aiohttp
from datetime import datetime
from typing import Dict, Any
from core.mq.worker_base import WorkerBase

logger = logging.getLogger("ExecutorL0")

class ExecutorL0(WorkerBase):
    """
    Tropa Frontal (Level 0).
    Velocidade extrema para domínios classificados como indefesos.
    Otimizado estruturalmente com aiohttp e concorrência máxima viável (Semaphore=20)
    """

    def __init__(self, redis_manager, worker_id: str = None, proxy_manager=None, 
                 concurrency: int = 20, db_manager=None, raw_store=None):
        super().__init__(
            redis_manager=redis_manager, 
            stream_name="stream:level_0", 
            group_name="workers_l0", 
            worker_id=worker_id, 
            concurrency=concurrency,
            proxy_manager=proxy_manager,
            db_manager=db_manager,
            raw_store=raw_store
        )
        self.session = None
        self.tier = 0

    async def _get_session(self):
        if self.session is None or self.session.closed:
            # TTL customizado em conexões e Header genérico, mas rapido.
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
        return self.session

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        logger.info(f"[L0] Extraindo {url}...")
        
        if not url:
            return False

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    import uuid
                    capture_id = str(uuid.uuid4())
                    content_hash = self.raw_store.calculate_hash(html_content)
                    
                    # 1. Persistência Bruta (Raw Capture Plane)
                    metadata = {
                        "capture_id": capture_id,
                        "mission_id": data.get("mission_id", "default"),
                        "job_id": data.get("job_id", "unknown"),
                        "url": url,
                        "executor_level": "L0-aiohttp",
                        "http_status": 200,
                        "content_type": response.headers.get("Content-Type", "text/html"),
                        "captured_at": str(datetime.utcnow()),
                        "content_hash": content_hash
                    }
                    
                    raw_uri, meta_uri = await self.raw_store.save_artifact(
                        metadata["mission_id"], capture_id, html_content, metadata
                    )
                    
                    logger.info(f"[L0] Sucesso: {url} | Raw: {raw_uri} | {len(html_content)} bytes")
                    
                    # 2. Emissão de Evento Desacoplado (Artifact-Oriented)
                    capture_event = data.copy()
                    capture_event.update({
                        "capture_id": capture_id,
                        "raw_uri": raw_uri,
                        "metadata_uri": meta_uri,
                        "executor_level": "L0-aiohttp",
                        "http_status": 200,
                        "content_hash": content_hash
                    })
                    
                    # Notifica o Controle de Captura (Control Plane ouvirá isso)
                    await self.rm.client.xadd("stream:captured_raw", capture_event)
                    
                    return True
                    
                elif response.status in (403, 401, 429, 503):
                    # WAF Lockout Detectado
                    logger.warning(f"[L0] Bloqueio {response.status} em {url}. Escalando para L12.")
                    # Escalação Automática: Joga na fila de TLS Spoofing
                    payload = data.copy()
                    payload.update({"escalated_from": "L0"})
                    await self.rm.client.xadd("stream:level_12", payload)
                    return True # Retona True pro ACK matar a msg na fila L0. O novo worker L12 assume.

                elif response.status == 404:
                    logger.error(f"[L0] URL Morta 404 {url}. Descartando.")
                    return True
                
                else: # 500 etc
                    return False

        except Exception as e:
            logger.error(f"[L0] Falha Execepcional {url}: {e}")
            return False

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
