import logging
from typing import Dict, Any
from curl_cffi.requests import AsyncSession
from core.mq.worker_base import WorkerBase

logger = logging.getLogger("ExecutorL12")

class ExecutorL12(WorkerBase):
    """
    Executor Intermediário (Level 1-2).
    Especializado em Evasão TLS (TLS Spoofing) para passar por escudos Cloudflare simples.
    Herda da WorkerBase para gestão automática de fila e ACK.
    """

    def __init__(self, redis_manager, worker_id: str, proxy_manager=None, concurrency: int = 15):
        super().__init__(
            redis_manager=redis_manager, 
            stream_name="stream:level_12", 
            group_name="workers_l12", 
            worker_id=worker_id, 
            concurrency=concurrency,
            proxy_manager=proxy_manager
        )
        self.impersonate_browser = "chrome120"
        self.tier = 2 # Pode ser elevado para 3 se o ProxyManager assim decidir

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        escalated_from = data.get("escalated_from", "Routing")
        logger.info(f"[L12] Executando {url} (Origem: {escalated_from}) com TLS Spoofing {self.impersonate_browser}...")
        
        if not url:
            return False

        try:
            # Resolvendo Tier e Proxy
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            target_tier = self.tier
            proxy_url = None
            
            if self.proxy_manager:
                target_tier = await self.proxy_manager.resolve_tier_for_domain(domain, self.tier)
                proxy_url = self.proxy_manager.get_proxy_string_for_tier(target_tier)

            # AsyncSession herda do request.Session com suporte assíncrono real CFFI
            async with AsyncSession() as session:
                response = await session.get(
                    url,
                    impersonate=self.impersonate_browser,
                    proxy=proxy_url,
                    timeout=15
                )
                
                if response.status_code == 200 and "Just a moment" not in response.text:
                    html_content = response.text
                    
                    logger.info(f"[L12] 🛡️ Evasão Bem Sucedida em {url} | 200 OK | {len(html_content)} bytes")
                    
                    # Enfileirando na limpeza (preservando metadata)
                    payload = data.copy()
                    payload.update({
                        "html_content": html_content,
                        "executor_level": "L12-curlcffi",
                        "status": "200"
                    })
                    await self.rm.client.xadd("stream:dataclear", payload)
                    
                    return True
                    
                elif response.status_code in (403, 401, 429, 503) or "Just a moment" in response.text:
                    # Cloudflare nos barrou mesmo com Chrome TLS. 
                    logger.warning(f"[L12] 🧱 Muro detectado em {url}. Status: {response.status_code}")
                    
                    # Se estamos usando proxy, notifica o rotator
                    if self.proxy_manager and target_tier >= 3:
                        rotator = self.proxy_manager.get_rotator_for_tier(target_tier)
                        if rotator:
                            await rotator.rotate_on_block(response.status_code)
 
                    # Escalação Automática Final se ainda não estivermos no Tier máximo do L12
                    payload = data.copy()
                    if target_tier < 3:
                         logger.info(f"[L12] Re-tentando {url} com Tier 3 (Mobile Proxy)...")
                         payload.update({"escalated_from": "L12-T2", "tier": "3"})
                         await self.rm.client.xadd("stream:level_12", payload)
                    else:
                         logger.warning(f"[L12] Tier 3 falhou. Escalando para L34 (Playwright).")
                         payload.update({"escalated_from": "L12-T3"})
                         await self.rm.client.xadd("stream:level_34", payload)
                         
                    return True # Tratado. Tira da fila L12.
                
                elif response.status_code == 404:
                    logger.error(f"[L12] URL Morta 404 {url}. Descartando.")
                    return True
                
                else: 
                    # 500, etc. Aciona o Retry Mechanism do WorkerBase (Death Letter / Backoff)
                    return False

        except Exception as e:
            logger.error(f"[L12] Falha CFFI Excepcional {url}: {e}")
            # Retorna False para que o mecanismo de erro (handle_failure da WorkerBase) atue
            return False
