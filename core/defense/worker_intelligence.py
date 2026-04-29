
import logging
from typing import Dict, Any
from core.mq.worker_base import WorkerBase
from core.defense.intelligence import DefenseIntelligence, DefenseLevel

logger = logging.getLogger("WorkerIntelligence")

class WorkerIntelligence(WorkerBase):
    """
    O Radar do Batalhão com Governança.
    Classifica URLs, aplica Robots.txt e registra falhas no Control Plane.
    """
    def __init__(self, redis_manager, intelligence_service: DefenseIntelligence, 
                 worker_id: str = None, db_manager=None, raw_store=None):
        super().__init__(
            redis_manager=redis_manager,
            stream_name="stream:ingestion",
            group_name="workers_intelligence",
            worker_id=worker_id,
            concurrency=50,
            db_manager=db_manager,
            raw_store=raw_store
        )
        self.intelligence = intelligence_service

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        mission_id = data.get("mission_id", "default")
        respect_robots = data.get("respect_robots", "true").lower() == "true"
        
        if not url:
            return False

        logger.info(f"🔍 [RADAR] Analisando: {url} | Missão: {mission_id}")
        
        try:
            level, compliance = await self.intelligence.classify_url(url, respect_robots=respect_robots)
            
            # 1. Verificação de Compliance (Robots.txt)
            if compliance == "DISALLOWED":
                logger.warning(f"🛑 Missão Abortada: {url} viola robots.txt.")
                
                # Registro Único no Control Plane (Fase 4)
                if self.db_manager:
                    await self.db_manager.register_dead_letter(
                        mission_id=mission_id,
                        url=url,
                        stage="intelligence",
                        failure_type="ROBOTS_DISALLOWED",
                        failure_reason="Violação de Robots.txt detectada pelo Radar",
                        payload_ref=data
                    )
                else:
                    # Fallback técnico apenas se o DB estiver fora (Segurança de Dados)
                    await self.rm.client.xadd("stream:dead_letters", {
                        "mission_id": mission_id,
                        "url": url,
                        "reason": "ROBOTS_DISALLOWED",
                        "infra_status": "db_offline"
                    })
                return True

            # 2. Roteamento por Nível de Defesa (WAF)
            force_level = data.get("force_level", "auto")
            
            if force_level == "0":
                target_stream = "stream:level_0"
            elif force_level == "12":
                target_stream = "stream:level_12"
            elif force_level == "34":
                target_stream = "stream:level_34"
            else:
                target_stream = "stream:level_0"
                if level == DefenseLevel.LEVEL_1 or level == DefenseLevel.LEVEL_2:
                    target_stream = "stream:level_12"
                elif level == DefenseLevel.LEVEL_3 or level == DefenseLevel.LEVEL_4:
                    target_stream = "stream:level_34"
            
            logger.info(f"🎯 Sonar: {level.name} -> {target_stream}")
            
            # Dispatch para os Executors
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
