# Blueprint Tecnico - Grande Desacoplamento

## Objetivo

Este repositorio deixa de ser um sistema hibrido de `crawler + RAG` e passa a ser exclusivamente a plataforma de `Capture & Curation Plane` da NeuralSafety.

Contrato futuro da branch:

- entrada: missoes, politicas de captura e politicas de curadoria
- processamento: roteamento, coleta, persistencia bruta, limpeza e homologacao
- saida: artefatos curados rastreaveis e catalogados
- exclusao: chat, serving semantico, vetorizacao, ChromaDB, FastAPI de RAG e memoria conversacional

---

## Macroarquitetura Alvo

```text
[Mission Ingest]
      |
      v
[Control Plane]
- PostgreSQL
- missao
- politica
- catalogo
- auditoria
      |
      v
[Execution Plane]
- Redis Streams
- Intelligence
- L0 / L12 / L34
      |
      v
[Raw Capture Plane]
- disco local / MinIO / S3
- HTML/JSON bruto
- metadados tecnicos
      |
      v
[Curation Plane]
- WorkerDataClear
- regras versionadas
- reprocessamento independente
      |
      v
[Curated Store]
- JSONL homologado
- manifests
- particao por missao/data
      |
      v
[Observability + DLQ]
- metricas
- falhas
- retries
- custo operacional
```

---

## Planos da Arquitetura

### 1. Control Plane

Responsabilidade:

- persistir estado de longo prazo
- governar missoes, politicas, capturas e artefatos
- manter rastreabilidade e replay

Tecnologia alvo:

- PostgreSQL

Entidades minimas:

- `missions`
- `mission_policies`
- `captures`
- `curation_runs`
- `curated_artifacts`
- `dead_letters`

### 2. Execution Plane

Responsabilidade:

- coordenacao assincrona de execucao
- roteamento por complexidade tecnica
- coleta resiliente em escala

Tecnologia alvo:

- Redis Streams
- workers especializados

Componentes:

- `RedisManager`
- `WorkerIntelligence`
- `ExecutorL0`
- `ExecutorL12`
- `ExecutorL34`

### 3. Raw Capture Plane

Responsabilidade:

- persistir todo material original antes da limpeza
- preservar evidencia tecnica da coleta
- permitir replay sem nova raspagem

Tecnologia alvo:

- storage local, MinIO ou S3

Artefatos:

- HTML bruto
- JSON bruto
- metadados de captura
- status HTTP
- headers
- executor utilizado
- hash do conteudo

### 4. Curation Plane

Responsabilidade:

- transformar bruto em dataset homologado
- aplicar filtro de PII
- normalizar schema
- gerar `semantic_chunks`
- registrar versao de regra

Componentes:

- `WorkerDataClear`
- `run_dataclear_job`
- `DataClearStage`

### 5. Curated Store

Responsabilidade:

- armazenar a saida oficial desta branch
- servir como contrato para consumidores externos
- permitir particionamento por missao e data

Artefatos:

- `dataset.jsonl`
- `manifest.json`
- relatorios auxiliares de auditoria

---

## Contratos de Dados

### Evento de ingestao

Fila: `stream:ingestion`

```json
{
  "mission_id": "uuid",
  "job_id": "cliente_alpha_001",
  "url": "https://dominio.com/pagina",
  "respect_robots": "true",
  "force_level": "auto",
  "ingested_at": "timestamp"
}
```

### Evento de captura concluida

Fila: `stream:captured_raw`

```json
{
  "capture_id": "uuid",
  "mission_id": "uuid",
  "job_id": "cliente_alpha_001",
  "url": "https://dominio.com/pagina",
  "raw_uri": "s3://bucket/raw/2026/04/29/uuid.html.gz",
  "metadata_uri": "s3://bucket/raw/2026/04/29/uuid.meta.json",
  "executor_level": "L12-curlcffi",
  "http_status": "200",
  "content_type": "text/html",
  "captured_at": "2026-04-29T12:00:00Z",
  "content_hash": "sha256..."
}
```

### Evento de curadoria pendente

Fila: `stream:dataclear`

Regra:

- transportar referencia de artefato
- nunca transportar `html_content` bruto na mensagem

### Artefato curado homologado

Formato: JSONL

```json
{
  "capture_id": "uuid",
  "mission_id": "uuid",
  "job_id": "cliente_alpha_001",
  "id_hash": "sha256...",
  "url": "https://dominio.com/artigo",
  "domain": "dominio.com",
  "crawl_timestamp": "2026-04-29T12:00:00Z",
  "schema_version": "v3_curated",
  "rule_version": "dataclear_2026_04",
  "executor": "L12-curlcffi",
  "data": {
    "title": "Titulo",
    "markdown_body": "conteudo limpo",
    "semantic_chunks": []
  },
  "compliance": {
    "pii_filtered": true,
    "gdpr_status": "compliant"
  },
  "quality": {
    "fidelity_score": 0.91
  }
}
```

---

## Modulos que Permanecem

- `core/main_batalhao.py`
- `core/mq/*`
- `core/defense/*`
- `core/executors/*`
- `core/stages/dataclear.py`
- `core/export/*`
- `ingest_batalhao.py`
- ferramentas de auditoria e operacao do crawler
- testes de persistencia, dataclear e missao

## Modulos que Saem desta Branch

- `rag_generator.py`
- `core/rag_service.py`
- `core/ingestor.py`
- `core/memory_manager.py`
- rotas FastAPI de chat ou ingestao semantica
- interface de RAG em `static/`
- dependencias operacionais de ChromaDB, FastAPI e OpenAI para o crawler

---

## Blueprint de Storage

### Raw Store

```text
raw/
  YYYY/
    MM/
      DD/
        mission_id/
          capture_id.html.gz
          capture_id.meta.json
```

Exemplo de `meta.json`:

```json
{
  "capture_id": "uuid",
  "mission_id": "uuid",
  "job_id": "cliente_alpha_001",
  "url": "https://dominio.com/pagina",
  "executor_level": "L34-playwright",
  "http_status": 200,
  "content_type": "text/html",
  "captured_at": "2026-04-29T12:00:00Z",
  "headers": {},
  "content_hash": "sha256..."
}
```

### Curated Store

```text
curated/
  YYYY/
    MM/
      DD/
        mission_id/
          dataset.jsonl
          manifest.json
```

---

## Modelo Minimo de PostgreSQL

### `missions`

- `id`
- `job_id`
- `status`
- `created_at`
- `finished_at`

### `mission_policies`

- `mission_id`
- `respect_robots`
- `force_level`
- `allowed_domains`
- `archetype`
- `fidelity_threshold`

### `captures`

- `id`
- `mission_id`
- `url`
- `executor_level`
- `http_status`
- `raw_uri`
- `metadata_uri`
- `status`
- `attempt_count`
- `captured_at`
- `content_hash`

### `curation_runs`

- `id`
- `capture_id`
- `rule_version`
- `status`
- `started_at`
- `finished_at`
- `error_reason`

### `curated_artifacts`

- `id`
- `mission_id`
- `capture_id`
- `artifact_uri`
- `schema_version`
- `record_count`
- `created_at`

### `dead_letters`

- `id`
- `mission_id`
- `url`
- `stage`
- `failure_type`
- `failure_reason`
- `payload_ref`
- `created_at`

---

## Streams Alvo

- `stream:ingestion`
- `stream:level_0`
- `stream:level_12`
- `stream:level_34`
- `stream:captured_raw`
- `stream:dataclear`
- `stream:curated_complete`
- `stream:dead_letters_retryable`
- `stream:dead_letters_terminal`

Objetivo:

- separar captura e curadoria
- separar falha recuperavel de falha terminal
- preservar a rastreabilidade do lifecycle

---

## Politica de DLQ

Categorias minimas:

- `NETWORK_TIMEOUT`
- `ROBOTS_DISALLOWED`
- `WAF_BLOCKED_PERSISTENT`
- `RAW_STORAGE_WRITE_FAILED`
- `RAW_ARTIFACT_MISSING`
- `DATACLEAR_PARSE_FAILED`
- `DATACLEAR_EMPTY_OUTPUT`
- `POLICY_VIOLATION`

Politica recomendada:

- timeout de rede: retry limitado com backoff
- bloqueio persistente: DLQ terminal
- falha de escrita em storage: retry prioritario
- falha de limpeza: replay local a partir do raw

---

## Observabilidade Minima Obrigatoria

### Por executor

- throughput por minuto
- taxa de sucesso
- taxa de escalonamento
- latencia media
- distribuicao por status HTTP

### Por curadoria

- backlog em `stream:dataclear`
- tempo medio de processamento
- taxa de descarte por fidelidade
- taxa de falha por regra

### Por missao

- URLs totais
- URLs novas
- capturas validas
- curados homologados
- custo estimado por executor

---

## Principios de Implementacao

- a fila transporta referencia, nao payload bruto
- o storage bruto e obrigatorio antes da limpeza
- a curadoria deve ser replayable
- o catalogo persistente nao pode ficar no Redis
- consumidor externo nao depende da estrutura interna de filas
- o produto final desta branch e `raw + curated artifacts`

---

## Definition of Done Arquitetural

A refatoracao estara conceitualmente correta quando:

- o crawler operar sem qualquer componente de RAG
- todo HTML bruto persistir antes do DataClear
- o DataClear puder ser reexecutado offline a partir do raw
- Redis nao for mais catalogo implicito de longo prazo
- PostgreSQL conseguir responder qual missao gerou qual artefato
- o produto final desta branch for exclusivamente `capture + curation`
