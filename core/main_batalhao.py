import asyncio
import logging
from core.utils import setup_logging
from core.mq.redis_manager import RedisManager

# Executors
from core.executors.executor_l0_aiohttp import ExecutorL0
from core.executors.executor_l12_curlcffi import ExecutorL12
from core.executors.executor_l34_playwright import ExecutorL34
from core.executors.worker_dataclear import WorkerDataClear
from core.proxies.proxy_intelligence import ProxyIntelligenceManager, SuccessRateTracker

# Defense & Compliance
from core.defense.intelligence import DefenseIntelligence
from core.defense.robots_guard import RobotsGuard
from core.defense.worker_intelligence import WorkerIntelligence

setup_logging()
logger = logging.getLogger("ComandanteBatalhao")

import os
PROXIES_SX_API_KEY = os.getenv("PROXIES_SX_API_KEY")

# Governança de Concorrência (Manipulável via .env)
CONCURRENCY_L0  = int(os.getenv("BATALHAO_CONCURRENCY_L0", "20"))
CONCURRENCY_L12 = int(os.getenv("BATALHAO_CONCURRENCY_L12", "15"))
CONCURRENCY_L34 = int(os.getenv("BATALHAO_CONCURRENCY_L34", "5"))

async def main():
    logger.info("🏁 Iniciando Máquina Motor de Guerra: Crawler de Batalhão...")
    logger.info(f"⚙️ Concorrência: L0={CONCURRENCY_L0} | L12={CONCURRENCY_L12} | L34={CONCURRENCY_L34}")

    if not PROXIES_SX_API_KEY:
        logger.error("❌ SEGURANÇA: Chave PROXIES_SX_API_KEY não encontrada no ambiente!")
        logger.warning("Os Proxies de Nível 3/4 operam em modo limitado (sem auto-rotação física).")
    
    # Registra e Inicia os Tiers do Redis
    rm = RedisManager(tenant_db_index=0)
    
    # Cada trabalhador tem a sua própria Stream e Group ID
    await rm.init_streams(["stream:level_0"], group_name="workers_l0")
    await rm.init_streams(["stream:level_12"], group_name="workers_l12")
    await rm.init_streams(["stream:level_34"], group_name="workers_l34")
    await rm.init_streams(["stream:dataclear"], group_name="workers_dataclear")
    # Ingress/Intelligence Stream
    await rm.init_streams(["stream:ingestion"], group_name="workers_intelligence")

    # 1.5 Inicializa Gerenciador de Proxies
    tracker = SuccessRateTracker(rm.client)
    proxy_manager = ProxyIntelligenceManager(
        tracker, 
        rotator_api="https://client.proxies.sx/api", 
        api_key=PROXIES_SX_API_KEY
    )

    # 1.6 Inteligência e Blindagem Robots.txt
    robots_guard = RobotsGuard(rm.client)
    intel_service = DefenseIntelligence(rm, robots_guard=robots_guard)
    w_intel = WorkerIntelligence(rm, intel_service, worker_id="sonar_Alpha")

    # 2. Inicializa os Esquadrões
    # Passamos o proxy_manager e a concorrência para todos os executores
    w_l0 = ExecutorL0(rm, worker_id="soldado_L0_Alpha", proxy_manager=proxy_manager, concurrency=CONCURRENCY_L0)
    w_l12 = ExecutorL12(rm, worker_id="soldado_L12_Ghost", proxy_manager=proxy_manager, concurrency=CONCURRENCY_L12)
    w_l34 = ExecutorL34(rm, worker_id="armadura_L34_Tank", proxy_manager=proxy_manager, concurrency=CONCURRENCY_L34)
    w_clear = WorkerDataClear(rm, worker_id="equipe_limpeza_Charlie")
    
    logger.info("⚔️ Robôs Despertos. Monitorando Filas de Scraping...")

    # 3. Trava Loop Principal para rodarem ao mesmo tempo
    try:
        await asyncio.gather(
            w_intel.listen(),
            w_l0.listen(),
            w_l12.listen(),
            w_l34.listen(),
            w_clear.listen()
        )
    except KeyboardInterrupt:
        logger.warning("Parada Solicitada pelo usuário. Desligando robôs...")
    finally:
        w_l0.stop()
        w_l12.stop()
        await w_l34.stop() # Espera fechar o Playwright limpo
        w_clear.stop()
        await rm.close()
        logger.info("💀 Batalhão Desmobilizado com Segurança.")

if __name__ == "__main__":
    asyncio.run(main())
