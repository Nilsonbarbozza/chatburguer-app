
import logging
import uuid
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession
from core.mq.worker_base import WorkerBase

logger = logging.getLogger("ExecutorL12")

class ExecutorL12(WorkerBase):
    """
    Executor Intermediário (Level 1-2).
    Especializado em Evasão TLS (TLS Spoofing) para passar por escudos Cloudflare simples.
    """

    def __init__(self, redis_manager, worker_id: str = None, proxy_manager=None, 
                 concurrency: int = 15, raw_store=None, db_manager=None):
        super().__init__(
            redis_manager=redis_manager, 
            stream_name="stream:level_12", 
            group_name="workers_l12", 
            worker_id=worker_id, 
            concurrency=concurrency,
            proxy_manager=proxy_manager,
            raw_store=raw_store,
            db_manager=db_manager
        )
        self.impersonate_browser = "chrome120"
        self.tier = 2

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        escalated_from = data.get("escalated_from", "Routing")
        logger.info(f"[L12] Executando {url} (Origem: {escalated_from}) com TLS Spoofing {self.impersonate_browser}...")
        
        if not url:
            return False

        try:
            domain = urlparse(url).netloc
            target_tier = self.tier
            proxy_url = None
            
            if self.proxy_manager:
                target_tier = await self.proxy_manager.resolve_tier_for_domain(domain, self.tier)
                proxy_url = self.proxy_manager.get_proxy_string_for_tier(target_tier)

            async with AsyncSession() as session:
                response = await session.get(
                    url,
                    impersonate=self.impersonate_browser,
                    proxy=proxy_url,
                    timeout=15
                )
                
                if response.status_code == 200 and "Just a moment" not in response.text:
                    html_content = response.text
                    
                    capture_id = str(uuid.uuid4())
                    content_hash = self.raw_store.calculate_hash(html_content)
                    
                    # 1. Persistência Bruta (Raw Capture Plane)
                    metadata = {
                        "capture_id": capture_id,
                        "mission_id": data.get("mission_id", "default"),
                        "job_id": data.get("job_id", "unknown"),
                        "url": url,
                        "executor_level": "L12-curlcffi",
                        "http_status": 200,
                        "content_type": response.headers.get("Content-Type", "text/html"),
                        "captured_at": str(datetime.utcnow()),
                        "content_hash": content_hash
                    }
                    
                    raw_uri, meta_uri = await self.raw_store.save_artifact(
                        metadata["mission_id"], capture_id, html_content, metadata
                    )
                    
                    logger.info(f"[L12] Evasão Sucesso: {url} | Raw: {raw_uri} | {len(html_content)} bytes")
                    
                    # 2. Emissão de Evento Desacoplado
                    capture_event = data.copy()
                    capture_event.update({
                        "capture_id": capture_id,
                        "raw_uri": raw_uri,
                        "metadata_uri": meta_uri,
                        "executor_level": "L12-curlcffi",
                        "http_status": 200,
                        "content_hash": content_hash
                    })
                    
                    await self.rm.client.xadd("stream:captured_raw", capture_event)
                    return True
                    
                elif response.status_code in (403, 401, 429, 503) or "Just a moment" in response.text:
                    logger.warning(f"[L12] 🧱 Muro detectado em {url}. Status: {response.status_code}")
                    
                    if self.proxy_manager and target_tier >= 3:
                        rotator = self.proxy_manager.get_rotator_for_tier(target_tier)
                        if rotator:
                            await rotator.rotate_on_block(response.status_code)

                    payload = data.copy()
                    if target_tier < 3:
                         logger.info(f"[L12] Re-tentando {url} com Tier 3 (Mobile Proxy)...")
                         payload.update({"escalated_from": "L12-T2", "tier": "3"})
                         await self.rm.client.xadd("stream:level_12", payload)
                    else:
                         logger.warning(f"[L12] Tier 3 falhou. Escalando para L34 (Playwright).")
                         payload.update({"escalated_from": "L12-T3"})
                         await self.rm.client.xadd("stream:level_34", payload)
                         
                    return True
                
                elif response.status_code == 404:
                    logger.error(f"[L12] URL Morta 404 {url}. Descartando.")
                    return True
                
                else: 
                    return False

        except Exception as e:
            logger.error(f"[L12] Falha CFFI Excepcional {url}: {e}")
            return False
