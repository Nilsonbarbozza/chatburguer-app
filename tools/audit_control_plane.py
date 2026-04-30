
import asyncio
import os
import logging
from core.mq.db_manager import DatabaseManager
from core.utils import setup_logging

setup_logging()
logger = logging.getLogger("AuditControlPlane")

async def run_audit():
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        logger.error("❌ Erro: Variável POSTGRES_URL não definida!")
        return

    db = DatabaseManager(dsn=postgres_url)
    logger.info(f"🔍 Iniciando Auditoria do Control Plane em {postgres_url.split('@')[-1]}...")

    try:
        await db.connect()
        logger.info("✅ Conexão com PostgreSQL: ESTABELECIDA")

        # 1. Métricas de Missões
        missions = await db.pool.fetch("SELECT id, job_id, status, created_at FROM missions ORDER BY created_at DESC LIMIT 5")
        print("\n--- [ Missões Recentes ] ---")
        if not missions:
            print("Nenhuma missão registrada.")
        for m in missions:
            print(f"ID: {m['id']} | Job: {m['job_id']} | Status: {m['status']} | Criada em: {m['created_at']}")

        # 2. Métricas de Captura
        stats = await db.pool.fetchrow("""
            SELECT 
                count(*) as total,
                count(CASE WHEN http_status = 200 THEN 1 END) as success,
                count(CASE WHEN http_status != 200 THEN 1 END) as failed
            FROM captures
        """)
        print("\n--- [ Estatísticas de Captura ] ---")
        print(f"Total de Capturas: {stats['total']}")
        print(f"Sucesso (200 OK): {stats['success']}")
        print(f"Falhas: {stats['failed']}")

        # 3. Auditoria de Falhas (Dead Letters)
        failures = await db.pool.fetch("SELECT failure_type, count(*) as qty FROM dead_letters GROUP BY failure_type")
        print("\n--- [ Mapa de Falhas (DLQ) ] ---")
        if not failures:
            print("Nenhuma falha registrada.")
        for f in failures:
            print(f"Tipo: {f['failure_type']} | Qtd: {f['qty']}")

        # 4. Verificação de Integridade de Artefatos
        raw_count = await db.pool.fetchval("SELECT count(*) FROM captures WHERE raw_uri IS NOT NULL")
        print(f"\n✅ Integridade: {raw_count}/{stats['total']} capturas possuem lastro no Raw Store.")

    except Exception as e:
        logger.error(f"❌ Falha na Auditoria: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(run_audit())
