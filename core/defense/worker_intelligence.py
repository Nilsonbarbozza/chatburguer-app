import logging
from typing import Dict, Any
from core.mq.worker_base import WorkerBase
from core.defense.intelligence import DefenseIntelligence, DefenseLevel

logger = logging.getLogger("WorkerIntelligence")

class WorkerIntelligence(WorkerBase):
    """
    O Radar do Batalhão.
    Classifica URLs, aplica Robots.txt e despacha para a esquadra correta.
    """
    def __init__(self, redis_manager, intelligence_service: DefenseIntelligence, worker_id: str):
        super().__init__(
            redis_manager=redis_manager,
            stream_name="stream:ingestion",
            group_name="workers_intelligence",
            worker_id=worker_id,
            concurrency=50 # Altíssima concorrência pois é majoritariamente IO de Probe
        )
        self.intelligence = intelligence_service

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        # Flag dinâmica de respeito ao robots (Padrão: True)
        respect_robots = data.get("respect_robots", "true").lower() == "true"
        
        if not url:
            return False

        logger.info(f"🔍 Analisando alvo: {url} (RespectRobots={respect_robots})")
        
        try:
            level, compliance = await self.intelligence.classify_url(url, respect_robots=respect_robots)
            
            # 1. Verificação de Compliance (Robots.txt)
            if compliance == "DISALLOWED":
                logger.warning(f"🛑 Missão Abortada: {url} viola robots.txt. Enviando para auditoria.")
                await self.rm.client.xadd("stream:dead_letters", {
                    "url": url,
                    "reason": "ROBOTS_DISALLOWED",
                    "compliance_status": compliance
                })
                return True # ACK - Processado (negado)

            # 2. Roteamento por Nível de Defesa (WAF) ou Override Manual
            force_level = data.get("force_level", "auto")
            
            if force_level == "0":
                target_stream = "stream:level_0"
                logger.info(f"⚡ OVERRIDE: Forçando execução em {target_stream} para {url}")
            elif force_level == "12":
                target_stream = "stream:level_12"
                logger.info(f"⚡ OVERRIDE: Forçando execução em {target_stream} para {url}")
            elif force_level == "34":
                target_stream = "stream:level_34"
                logger.info(f"⚡ OVERRIDE: Forçando execução em {target_stream} para {url}")
            else:
                # Lógica Automática do Sonar
                target_stream = "stream:level_0"
                if level == DefenseLevel.LEVEL_1 or level == DefenseLevel.LEVEL_2:
                    target_stream = "stream:level_12"
                elif level == DefenseLevel.LEVEL_3 or level == DefenseLevel.LEVEL_4:
                    target_stream = "stream:level_34"
                logger.info(f"🎯 Sonar classifica como {level.name}. Roteando para {target_stream}")
            
            # Dispatch para os Executors (Preservando todo o metadata, ex: job_id)
            payload = data.copy()
            payload.update({
                "defense_level": str(level.value),
                "compliance_status": compliance,
                "msg_origin": "intelligence"
            })
            
            await self.rm.client.xadd(target_stream, payload)
            
            return True

        except Exception as e:
            logger.error(f"Erro no Radar de Inteligência para {url}: {e}")
            return False
