import asyncio
import logging
import os
from core.utils import setup_logging

# MQ & Data
from core.mq.redis_manager import RedisManager
from core.mq.db_manager import DatabaseManager
from core.export.raw_store import RawArtifactStore

# Executors
from core.executors.executor_l0_aiohttp import ExecutorL0
from core.executors.executor_l12_curlcffi import ExecutorL12
from core.executors.executor_l34_playwright import ExecutorL34
from core.executors.worker_dataclear import WorkerDataClear
from core.executors.worker_capture_control import CaptureControlWorker
from core.proxies.proxy_intelligence import ProxyIntelligenceManager, SuccessRateTracker

# Defense & Compliance
from core.defense.intelligence import DefenseIntelligence
from core.defense.robots_guard import RobotsGuard
from core.defense.worker_intelligence import WorkerIntelligence

setup_logging()
logger = logging.getLogger("ComandanteBatalhao")

PROXIES_SX_API_KEY = os.getenv("PROXIES_SX_API_KEY")
POSTGRES_URL = os.getenv("POSTGRES_URL")

# Governança de Concorrência (Manipulável via .env)
CONCURRENCY_L0  = int(os.getenv("BATALHAO_CONCURRENCY_L0", "20"))
CONCURRENCY_L12 = int(os.getenv("BATALHAO_CONCURRENCY_L12", "15"))
CONCURRENCY_L34 = int(os.getenv("BATALHAO_CONCURRENCY_L34", "5"))

# Definição de Papéis (Roles) para Escala Horizontal
ROLES = os.getenv("BATALHAO_ROLES", "intelligence,capture_control,l0,l12,l34,dataclear").split(",")
ROLES = [r.strip().lower() for r in ROLES]

async def main():
    logger.info("🏁 Iniciando Máquina Motor de Guerra: Crawler de Batalhão...")
    logger.info(f"⚙️ Concorrência: L0={CONCURRENCY_L0} | L12={CONCURRENCY_L12} | L34={CONCURRENCY_L34}")

    if not PROXIES_SX_API_KEY:
        logger.error("❌ SEGURANÇA: Chave PROXIES_SX_API_KEY não encontrada no ambiente!")
        logger.warning("Os Proxies de Nível 3/4 operam em modo limitado (sem auto-rotação física).")
    
    # 1. Inicializa Gerenciadores de Infraestrutura
    rm = RedisManager(tenant_db_index=0)
    db = DatabaseManager(dsn=POSTGRES_URL)
    raw_store = RawArtifactStore(base_path="data/raw")
    
    try:
        await db.connect()
    except Exception:
        logger.error("🛑 Falha Crítica: Não foi possível conectar ao Control Plane (PostgreSQL).")
        # Por enquanto permitimos rodar sem DB para não travar dev, 
        # mas em produção isso deve ser fatal.
    
    # Registra e Inicia os Tiers do Redis
    await rm.init_streams(["stream:level_0"], group_name="workers_l0")
    await rm.init_streams(["stream:level_12"], group_name="workers_l12")
    await rm.init_streams(["stream:level_34"], group_name="workers_l34")
    await rm.init_streams(["stream:captured_raw"], group_name="workers_capture_control")
    await rm.init_streams(["stream:dataclear"], group_name="workers_dataclear")
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
        w_intel = WorkerIntelligence(
            rm, intel_service, 
            db_manager=db, raw_store=raw_store
        )
        tasks.append(w_intel.listen())
        logger.info("📡 Radar de Inteligência Ativado.")

    # 2. Inicializa os Esquadrões (Baseado nas Roles)
    if "capture_control" in ROLES:
        w_cap = CaptureControlWorker(
            rm, db_manager=db, raw_store=raw_store
        )
        tasks.append(w_cap.listen())
        logger.info("🚦 Controlador de Captura Ativado.")

    if "l0" in ROLES:
        w_l0 = ExecutorL0(
            rm, proxy_manager=proxy_manager, concurrency=CONCURRENCY_L0,
            db_manager=db, raw_store=raw_store
        )
        tasks.append(w_l0.listen())
        logger.info("⚡ Executor L0 (aiohttp) Ativado.")

    if "l12" in ROLES:
        w_l12 = ExecutorL12(
            rm, proxy_manager=proxy_manager, concurrency=CONCURRENCY_L12,
            db_manager=db, raw_store=raw_store
        )
        tasks.append(w_l12.listen())
        logger.info("🛡️ Executor L12 (curl_cffi) Ativado.")

    if "l34" in ROLES:
        w_l34 = ExecutorL34(
            rm, proxy_manager=proxy_manager, concurrency=CONCURRENCY_L34,
            db_manager=db, raw_store=raw_store
        )
        tasks.append(w_l34.listen())
        logger.info("💥 Executor L34 (Playwright) Ativado.")

    if "dataclear" in ROLES:
        w_clear = WorkerDataClear(
            rm, db_manager=db, raw_store=raw_store
        )
        tasks.append(w_clear.listen())
        logger.info("🧹 Equipe DataClear Ativada.")
    
    if not tasks:
        logger.error("🛑 Nenhuma ROLE válida definida. O Batalhão não tem ordens para agir.")
        await rm.close()
        await db.close()
        return

    logger.info(f"⚔️ Batalhão em Combate com {len(tasks)} frentes ativas. Monitorando...")

    # 3. Trava Loop Principal
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.warning("Parada Solicitada pelo usuário. Desligando robôs...")
    finally:
        await rm.close()
        await db.close()
        logger.info("💀 Batalhão Desmobilizado com Segurança.")

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
