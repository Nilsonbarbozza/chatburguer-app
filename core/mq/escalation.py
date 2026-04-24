import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger("EscalationEngine")

class EscalationEngine:
    """
    Camada 3.5: Retry + Escalation Engine.
    Atua acoplada ao WorkerBase para avaliar falhas puras e gerenciar Backoff ou descarte.
    """
    def __init__(self, redis_manager):
        self.rm = redis_manager

    async def handle_retry(self, stream_name: str, group_name: str, msg_id: str, data: Dict[str, Any], attempt: int = 1):
        """
        Determina se uma mensagem deve ser re-tentada, movida para uma rota morta, ou bloqueada.
        """
        max_attempts = 3
        url = data.get("url", "unknown")
        
        if attempt >= max_attempts:
            logger.error(f"[DLQ] URL {url} falhou {max_attempts}x. Exilando para Dead Letter Queue.")
            await self._send_to_dlq(stream_name, msg_id, data, reason="MAX_RETRIES_EXCEEDED")
            return
            
        # Backoff exponencial simples (2s -> 4s -> 8s)
        delay = 2 ** attempt
        logger.warning(f"Agendando retry para {url} em {delay}s (Tentativa {attempt}/{max_attempts})")
        
        # Em produção, usaremos uma ZSET de agendamento (Delayed Queue).
        # Por simplificação para este escopo, adicionamos na mesma fila após o sleep assíncrono.
        # Mas para não bloquear o Worker principal, rodariamaos numa Task independente.
        asyncio.create_task(self._delayed_requeue(delay, stream_name, msg_id, data, attempt))
        
        # Reconhecemos (ACK) a falha na stream original para não re-entregar instantaneamente.
        await self.rm.client.xack(stream_name, group_name, msg_id)

    async def _delayed_requeue(self, delay: int, stream_name: str, msg_id: str, data: Dict[str, Any], attempt: int):
        await asyncio.sleep(delay)
        # Adiciona de volta ao stream original, mas com metadata de tentativa
        new_data = {**data, "attempt": str(attempt + 1)}
        await self.rm.client.xadd(stream_name, new_data)
        logger.info(f"🔁 URL {data.get('url')} re-inserida na fila {stream_name} após deley.")

    async def _send_to_dlq(self, origin_stream: str, msg_id: str, data: Dict[str, Any], reason: str):
        dlq_payload = {
            **data,
            "origin_stream": origin_stream,
            "original_msg_id": msg_id,
            "failure_reason": reason
        }
        await self.rm.client.xadd("stream:dead_letters", dlq_payload)
