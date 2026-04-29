import asyncio
import logging
import os
import socket
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger("WorkerBase")

class WorkerBase(ABC):
    """
    Classe Abstrata para Consumidores Redis Streams.
    Gerencia automaticamente Acknowledgment (ACK) ou roteamento para Dead Letter.
    """

    def __init__(self, redis_manager, stream_name: str, group_name: str, 
                 worker_id: str = None, concurrency: int = 10, 
                 proxy_manager=None, claim_interval: int = 60,
                 raw_store=None, db_manager=None):
        self.rm = redis_manager
        self.stream_name = stream_name
        self.group_name = group_name
        self.claim_interval = claim_interval # Segundos entre tentativas de resgate de msgs presas
        
        # Gera ID dinâmico se não for fornecido (Crucial para Escala Horizontal em Docker)
        self.worker_id = worker_id or os.getenv("HOSTNAME") or f"{socket.gethostname()}_{os.getpid()}"
        
        self.semaphore = asyncio.Semaphore(concurrency)
        self.proxy_manager = proxy_manager
        self.raw_store = raw_store
        self.db_manager = db_manager
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
        Registro de falha unificado no Control Plane (PostgreSQL).
        """
        url = data.get("url", "unknown")
        mission_id = data.get("mission_id", "default")
        
        logger.warning(f"❌ [FALHA] Processamento falhou para {url}. Registrando no Control Plane...")
        
        try:
            if self.db_manager:
                await self.db_manager.register_dead_letter(
                    mission_id=mission_id,
                    url=url,
                    stage=self.stream_name.split(':')[-1],
                    failure_type="OPERATIONAL_FAILURE",
                    failure_reason="Erro não tratado no worker ou limite de retries atingido",
                    payload_ref=data
                )
            else:
                # Fallback técnico apenas se o DB não estiver injetado
                await self.rm.client.xadd("stream:dead_letters", {"original_stream": self.stream_name, **data})
            
            # Acknowledge para evitar loop infinito de mensagens defeituosas
            await self.rm.client.xack(self.stream_name, self.group_name, msg_id)
        except Exception as e:
            logger.error(f"⚠️ Erro Crítico no tratamento de falha {msg_id}: {e}")

    async def claim_stuck_messages(self):
        """
        Tarefa de Background: Resgata mensagens que ficaram 'presas' por falha de outros workers.
        XAUTOCLAIM transfere a posse da mensagem para o worker atual se ela estiver pendente há muito tempo.
        """
        while self.running:
            try:
                # Tenta resgatar mensagens pendentes há mais de 5 minutos (300.000 ms)
                # O parâmetro 'min_idle_time' define o tempo de espera antes de considerar 'abandonada'
                result = await self.rm.client.xautoclaim(
                    self.stream_name, 
                    self.group_name, 
                    self.worker_id, 
                    min_idle_time=300000, 
                    start_id="0-0",
                    count=5
                )
                
                # result: [next_id, [ (msg_id, data), ... ], [deleted_ids]]
                if result and result[1]:
                    logger.warning(f"🧟 [RESGATE] Worker {self.worker_id} reivindicou {len(result[1])} mensagens abandonadas no stream {self.stream_name}.")
                    # As mensagens resgatadas serão processadas no loop principal via backlog '0' 
                    # ou podemos disparar aqui. Para manter o semáforo, apenas o claim já as coloca no nosso PEL.
                
            except Exception as e:
                logger.error(f"Erro no XAUTOCLAIM do worker {self.worker_id}: {e}")
            
            await asyncio.sleep(self.claim_interval)

    async def listen(self, check_backlog: bool = True):
        """
        Loop principal do Consumidor no Redis Streams.
        """
        self.running = True
        logger.info(f"Worker {self.worker_id} escutando o stream {self.stream_name}...")

        # Inicia tarefa de monitoramento de msgs presas
        asyncio.create_task(self.claim_stuck_messages())

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
