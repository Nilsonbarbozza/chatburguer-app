CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Schema Inicial do Batalhão NeuralSafety (Control Plane)
-- Branch: grande-desacoplamento

-- 1. Missões: A unidade fundamental de trabalho
CREATE TABLE IF NOT EXISTS missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active', -- active, finished, failed, paused
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- 2. Políticas de Missão: Regras que governam a execução
CREATE TABLE IF NOT EXISTS mission_policies (
    id SERIAL PRIMARY KEY,
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    respect_robots BOOLEAN DEFAULT TRUE,
    force_level VARCHAR(50) DEFAULT 'auto',
    allowed_domains TEXT, -- Comma separated ou JSON array
    archetype VARCHAR(50) DEFAULT 'blog',
    fidelity_threshold FLOAT DEFAULT 0.6,
    redact_pii BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Capturas: Registro de cada material bruto coletado
CREATE TABLE IF NOT EXISTS captures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    executor_level VARCHAR(50) NOT NULL, -- L0, L12, L34
    http_status INTEGER,
    raw_uri TEXT NOT NULL,      -- file://... ou s3://...
    metadata_uri TEXT NOT NULL, -- file://... ou s3://...
    content_hash VARCHAR(255),
    status VARCHAR(50) DEFAULT 'captured', -- captured, processed, failed
    attempt_count INTEGER DEFAULT 1,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_log TEXT
);

-- 4. Execuções de Curadoria (Refino)
CREATE TABLE IF NOT EXISTS curation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capture_id UUID NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
    mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, completed, failed
    metadata JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE,
    error_reason TEXT
);

-- 5. Artefatos Curados: O produto final homologado (Data Lake Reference)
CREATE TABLE IF NOT EXISTS curated_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curation_run_id UUID REFERENCES curation_runs(id) ON DELETE CASCADE,
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    capture_id UUID NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,      -- file://...
    record_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Dead Letter Queue: Catalogação de Falhas Terminais
CREATE TABLE IF NOT EXISTS dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES missions(id),
    url TEXT NOT NULL,
    stage VARCHAR(50) NOT NULL, -- ingestion, capture, curation
    failure_type VARCHAR(100) NOT NULL, -- NETWORK_TIMEOUT, ROBOTS_DISALLOWED, etc.
    failure_reason TEXT,
    payload_ref JSONB, -- Referência ao que causou a falha
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_captures_mission ON captures(mission_id);
CREATE INDEX IF NOT EXISTS idx_captures_url ON captures(url);
CREATE INDEX IF NOT EXISTS idx_curated_mission ON curated_artifacts(mission_id);
CREATE INDEX IF NOT EXISTS idx_dead_letters_mission ON dead_letters(mission_id);
