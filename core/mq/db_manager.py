
import os
import logging
import asyncpg
from typing import Dict, Any, Optional, List

logger = logging.getLogger("DatabaseManager")

class DatabaseManager:
    """
    Control Plane Manager (PostgreSQL).
    Responsável pela governança, catálogo e rastreabilidade da NeuralSafety.
    """
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("POSTGRES_URL")
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Inicializa o pool de conexões."""
        if not self.dsn:
            logger.error("❌ POSTGRES_URL não configurada no ambiente!")
            return
        
        try:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)
            logger.info("📡 Conexão com PostgreSQL (Control Plane) estabelecida.")
        except Exception as e:
            logger.error(f"❌ Falha ao conectar ao PostgreSQL: {e}")
            raise

    async def close(self):
        """Encerra o pool de conexões."""
        if self.pool:
            await self.pool.close()
            logger.info("💀 Conexão com PostgreSQL encerrada.")

    # --- MISSIONS ---

    async def create_mission(self, job_id: str, metadata: Dict[str, Any] = None) -> str:
        """Cria uma nova missão e retorna seu ID."""
        query = """
            INSERT INTO missions (job_id, metadata)
            VALUES ($1, $2)
            RETURNING id;
        """
        async with self.pool.acquire() as conn:
            mission_id = await conn.fetchval(query, job_id, json.dumps(metadata or {}))
            return str(mission_id)

    async def register_policy(self, mission_id: str, policy: Dict[str, Any]):
        """Registra a política de execução de uma missão."""
        query = """
            INSERT INTO mission_policies (
                mission_id, respect_robots, force_level, allowed_domains, archetype, fidelity_threshold, redact_pii
            ) VALUES ($1, $2, $3, $4, $5, $6, $7);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                mission_id,
                policy.get("respect_robots", True),
                policy.get("force_level", "auto"),
                policy.get("allowed_domains", "*"),
                policy.get("archetype", "blog"),
                policy.get("fidelity_threshold", 0.6),
                policy.get("redact_pii", True)
            )

    # --- CAPTURES ---

    async def register_capture(self, mission_id: str, url: str, executor_level: str, 
                                 raw_uri: str, metadata_uri: str, http_status: int = 200, 
                                 content_hash: str = None, capture_id: str = None) -> str:
        """Registra uma nova captura no catálogo usando o ID original do executor."""
        query = """
            INSERT INTO captures (
                id, mission_id, url, executor_level, raw_uri, metadata_uri, http_status, content_hash
            ) VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, $8)
            RETURNING id;
        """
        async with self.pool.acquire() as conn:
            c_id = await conn.fetchval(
                query, capture_id, mission_id, url, executor_level, raw_uri, metadata_uri, http_status, content_hash
            )
            return str(c_id)

    # --- DEAD LETTER QUEUE ---

    async def register_dead_letter(self, mission_id: str, url: str, stage: str, 
                                     failure_type: str, failure_reason: str, 
                                     payload_ref: Dict[str, Any] = None):
        """Catalogação de falhas terminais no Control Plane (Audit Trail)."""
        query = """
            INSERT INTO dead_letters (
                mission_id, url, stage, failure_type, failure_reason, payload_ref
            ) VALUES ($1, $2, $3, $4, $5, $6);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query, mission_id, url, stage, failure_type, failure_reason, json.dumps(payload_ref or {})
            )

    # --- CURATION ---

    async def register_curation_run(self, capture_id: str, mission_id: str, 
                                     status: str = 'completed', metadata: Dict[str, Any] = None) -> str:
        """Registra o início/fim de um processo de curadoria."""
        query = """
            INSERT INTO curation_runs (capture_id, mission_id, status, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id;
        """
        async with self.pool.acquire() as conn:
            run_id = await conn.fetchval(query, capture_id, mission_id, status, json.dumps(metadata or {}))
            return str(run_id)

    async def register_curated_artifact(self, curation_run_id: str, capture_id: str, 
                                          mission_id: str, storage_path: str, record_count: int):
        """Cataloga o artefato final (JSONL) no Data Lake."""
        query = """
            INSERT INTO curated_artifacts (curation_run_id, capture_id, mission_id, storage_path, record_count)
            VALUES ($1, $2, $3, $4, $5);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, curation_run_id, capture_id, mission_id, storage_path, record_count)

import json
