import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger("WorkerBase")

class WorkerBase(ABC):
    """
    Classe Abstrata para Consumidores Redis Streams.
    Gerencia automaticamente Acknowledgment (ACK) ou roteamento para Dead Letter.
    """

    def __init__(self, redis_manager, stream_name: str, group_name: str, worker_id: str, concurrency: int = 10, proxy_manager=None):
        self.rm = redis_manager
        self.stream_name = stream_name
        self.group_name = group_name
        self.worker_id = worker_id
        self.semaphore = asyncio.Semaphore(concurrency)
        self.proxy_manager = proxy_manager
        self.running = False
        self.tier = 0 # Default, will be overridden by subclasses

    @abstractmethod
    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        """
        Lógica de execução. Deve retornar True (sucesso) ou False (falha).
        """
        pass

    async def handle_failure(self, msg_id: str, data: Dict[str, Any]):
        """
        Escalonamento de Retry ou envio direto para Dead Letter Queue.
        """
        logger.warning(f"Processamento falhou para msg_id {msg_id}. Roteando falha...")
        try:
            # Exemplo Mínimo: envia pra log
            # TODO: Implemenar Exponential Backoff ou mover para stream:dead_letters
            await self.rm.client.xadd("stream:dead_letters", {"original_stream": self.stream_name, **data})
            # Acknowledge the failed message from the original stream so it doesn't loop forever
            await self.rm.client.xack(self.stream_name, self.group_name, msg_id)
        except Exception as e:
            logger.error(f"Erro Crítico ao rotear falha {msg_id}: {e}")

    async def listen(self, check_backlog: bool = True):
        """
        Loop principal do Consumidor no Redis Streams.
        """
        self.running = True
        logger.info(f"Worker {self.worker_id} escutando o stream {self.stream_name}...")

        # Primeiro tentamos processar msgs pendentes do nosso worker ("0")
        last_id = "0" if check_backlog else ">"

        while self.running:
            try:
                # Bloqueia por 2000ms esperando por nova mensagem
                streams_to_read = {self.stream_name: last_id}
                response = await self.rm.client.xreadgroup(
                    self.group_name, 
                    self.worker_id, 
                    streams_to_read, 
                    count=10, 
                    block=2000
                )

                if response:
                    for stream_name, messages in response:
                        for msg_id, data in messages:
                            async with self.semaphore:
                                success = await self.process_message(msg_id, data)
                                
                                # RECORDING INTELLIGENCE: 
                                # Se houver um proxy_manager e a URL estiver presente no payload
                                if self.proxy_manager and "url" in data:
                                    from urllib.parse import urlparse
                                    domain = urlparse(data["url"]).netloc
                                    await self.proxy_manager.tracker.record_attempt(domain, self.tier, success)

                                if success:
                                    # Se Sucesso Garantido, enviamos o ACK
                                    await self.rm.client.xack(self.stream_name, self.group_name, msg_id)
                                else:
                                    await self.handle_failure(msg_id, data)
                
                # Após limpar o backlog próprio ("0"), muda para aguardar novas mensagens (">")
                last_id = ">"

            except Exception as e:
                logger.error(f"Worker {self.worker_id} falhou no listener: {e}")
                await asyncio.sleep(2) # Backoff de seguranca para nao sobrecarregar o redis

    def stop(self):
        self.running = False
