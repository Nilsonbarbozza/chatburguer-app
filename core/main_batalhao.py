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

# Definição de Papéis (Roles) para Escala Horizontal
# Ex: BATALHAO_ROLES=intelligence,l0
ROLES = os.getenv("BATALHAO_ROLES", "intelligence,l0,l12,l34,dataclear").split(",")
ROLES = [r.strip().lower() for r in ROLES]

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

    tasks = []

    # 1.6 Inteligência e Blindagem Robots.txt
    if "intelligence" in ROLES:
        robots_guard = RobotsGuard(rm.client)
        intel_service = DefenseIntelligence(rm, robots_guard=robots_guard)
        w_intel = WorkerIntelligence(rm, intel_service)
        tasks.append(w_intel.listen())
        logger.info("📡 Radar de Inteligência Ativado.")

    # 2. Inicializa os Esquadrões (Baseado nas Roles)
    if "l0" in ROLES:
        w_l0 = ExecutorL0(rm, proxy_manager=proxy_manager, concurrency=CONCURRENCY_L0)
        tasks.append(w_l0.listen())
        logger.info("⚡ Executor L0 (aiohttp) Ativado.")

    if "l12" in ROLES:
        w_l12 = ExecutorL12(rm, proxy_manager=proxy_manager, concurrency=CONCURRENCY_L12)
        tasks.append(w_l12.listen())
        logger.info("🛡️ Executor L12 (curl_cffi) Ativado.")

    if "l34" in ROLES:
        w_l34 = ExecutorL34(rm, proxy_manager=proxy_manager, concurrency=CONCURRENCY_L34)
        tasks.append(w_l34.listen())
        logger.info("💥 Executor L34 (Playwright) Ativado.")

    if "dataclear" in ROLES:
        w_clear = WorkerDataClear(rm)
        tasks.append(w_clear.listen())
        logger.info("🧹 Equipe DataClear Ativada.")
    
    if not tasks:
        logger.error("🛑 Nenhuma ROLE válida definida. O Batalhão não tem ordens para agir.")
        await rm.close()
        return

    logger.info(f"⚔️ Batalhão em Combate com {len(tasks)} frentes ativas. Monitorando...")

    # 3. Trava Loop Principal
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.warning("Parada Solicitada pelo usuário. Desligando robôs...")
    finally:
        # Nota: O stop aqui é simplificado, o ideal em escala é lidar com SIGTERM
        await rm.close()
        logger.info("💀 Batalhão Desmobilizado com Segurança.")

if __name__ == "__main__":
    asyncio.run(main())
