import logging
import aiohttp
from typing import Dict, Any
from core.mq.worker_base import WorkerBase

logger = logging.getLogger("ExecutorL0")

class ExecutorL0(WorkerBase):
    """
    Tropa Frontal (Level 0).
    Velocidade extrema para domínios classificados como indefesos.
    Otimizado estruturalmente com aiohttp e concorrência máxima viável (Semaphore=20)
    """

    def __init__(self, redis_manager, worker_id: str = None, proxy_manager=None, concurrency: int = 20):
        super().__init__(
            redis_manager=redis_manager, 
            stream_name="stream:level_0", 
            group_name="workers_l0", 
            worker_id=worker_id, 
            concurrency=concurrency,
            proxy_manager=proxy_manager
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
                    
                    # -> [!] PONTO DE INTEGRAÇÃO COM PIPELINE DE LIMPEZA
                    # Chamaremos o pipeline DataClear (que não roda aqui isolado)
                    # O ideal na arquitetura final é enviar o HTML para a fila `stream:dataclear`
                    # para que os workers de CPU Heavy tratem NLP sem parar o scrapper de IO.
                    # Mas por simplifição atual, vamos logar apenas.
                    
                    logger.info(f"[L0] Sucesso ABSOLUTO em {url} | Status Real 200 | {len(html_content)} bytes")
                    
                    # Vamos enfileirar o payload bruto na fila de Limpeza (DataClear)
                    payload = data.copy()
                    payload.update({
                        "html_content": html_content,
                        "executor_level": "L0-aiohttp",
                        "status": "200"
                    })
                    await self.rm.client.xadd("stream:dataclear", payload)
                    
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
