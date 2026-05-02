# Walkthrough: O Grande Desacoplamento (Batalhao v4.0)

Este documento descreve a nova arquitetura do Batalhao apos o inicio do `Grande Desacoplamento`.

Objetivo desta versao do walkthrough:

- orientar o squad de codigo com base no estado real do repositorio
- separar claramente o que ja foi implementado do que ainda depende de consolidacao
- evitar que o time trate arquitetura-alvo como deploy concluido

---

## Resumo Executivo

O repositorio deixou de ter o RAG como responsabilidade principal e passou a ser tratado como `Capture & Curation Plane`.

Mudanca central:

- antes: o sistema misturava coleta web, curadoria, vetorizacao e serving
- agora: o foco desta branch e capturar conteudo bruto, persisti-lo, curar o material e gerar artefatos homologados

O desacoplamento ja avancou de forma relevante, mas ainda existem itens de infraestrutura, deploy e observabilidade que precisam ser consolidados para considerar a arquitetura plenamente fechada.

---

## Estado Atual da Arquitetura

Hoje o sistema esta organizado em tres eixos principais:

### 1. Control Plane

Responsabilidade:

- registrar missoes
- registrar politicas
- catalogar capturas
- registrar falhas estruturadas

Implementacao atual:

- existe `DatabaseManager`
- existe schema SQL para PostgreSQL
- `ingest_batalhao.py` ja registra missao e politica
- `CaptureControlWorker` ja registra captura

Status:

- `implementado no codigo`
- `nao consolidado no deploy`

Observacao:

- a camada existe no repositorio, mas o `docker-compose.yml` ainda nao sobe PostgreSQL nem injeta a infraestrutura completa descrita nesta arquitetura

### 2. Raw Capture Plane

Responsabilidade:

- persistir artefato bruto antes da curadoria
- remover payload pesado das filas
- permitir replay sem novo fetch web

Implementacao atual:

- existe `RawArtifactStore`
- os executores L0, L12 e L34 geram `capture_id`
- os executores salvam o bruto em `data/raw/`
- o evento de captura agora carrega `raw_uri` e metadados

Status:

- `implementado no codigo`
- `primeira versao funcional`

Observacao:

- a implementacao atual usa backend local `file://`
- ainda nao ha compressao, backend S3/MinIO ou abstracao completa de storage

### 3. Curation Plane

Responsabilidade:

- consumir artefatos brutos
- aplicar DataClear
- gerar saida curada com linhagem

Implementacao atual:

- `WorkerDataClear` passou a consumir `raw_uri`
- `DataClearStage` agora recebe `capture_id` e `mission_id`
- `DataLakeWriter` grava a saida curada com organizacao por missao e data

Status:

- `implementado no codigo`
- `precisa consolidacao operacional`

Observacao:

- o novo fluxo esta desenhado e implementado no codigo, mas ainda precisa convergir com infraestrutura, metricas e rotina oficial de operacao

---

## Mudancas Ja Implementadas no Repositorio

### 1. Purga do dominio RAG

Ja removido desta branch:

- `rag_generator.py`
- `core/rag_service.py`
- `core/ingestor.py`
- `core/memory_manager.py`
- interface estatica de RAG

Ja removido das dependencias principais:

- `chromadb`
- `openai`
- `fastapi`
- `uvicorn`
- `tiktoken`
- `python-multipart`

Leitura correta:

- esta branch ja nao deve ser tratada como repositorio de serving semantico
- o foco agora e exclusivamente crawler, captura e curadoria

### 2. Refatoracao dos executores

Implementado:

- `ExecutorL0` salva artefato bruto e emite evento de captura
- `ExecutorL12` segue o mesmo protocolo
- `ExecutorL34` persiste a DOM renderizada antes da curadoria

Contrato novo introduzido:

- a fila deixa de carregar `html_content`
- a fila passa a transportar referencia de artefato bruto

### 3. Novo fluxo de catalogacao

Implementado:

- `ingest_batalhao.py` cria missao no Control Plane
- `CaptureControlWorker` consome `stream:captured_raw`
- a captura e registrada no catalogo antes do envio para curadoria

### 4. Nova linhagem no artefato curado

Implementado:

- os registros curados passam a carregar `capture_id`
- os registros curados passam a carregar `mission_id`

Impacto:

- reprocessamento e auditoria ficam estruturalmente possiveis

---

## Mudancas Parcialmente Consolidadas

Os itens abaixo existem no codigo, mas ainda nao devem ser descritos para o time como "operacao completamente fechada":

### 1. PostgreSQL como fonte total de verdade

Situacao real:

- o `DatabaseManager` existe
- o schema existe
- parte do fluxo ja escreve no banco

Pendente:

- subir Postgres no deploy oficial
- parametrizar `POSTGRES_URL` em todos os servicos necessarios
- validar boot completo da stack com essa dependencia obrigatoria

### 2. Curated Store no deploy

Situacao real:

- o writer ja aponta para `data/curated/`

Pendente:

- alinhar `docker-compose.yml`
- revisar volumes e caminhos persistidos
- remover referencias antigas a `data/output`

### 3. DLQ e governanca de falhas

Situacao real:

- ja existe registro de falhas no PostgreSQL
- ainda existe envio para `stream:dead_letters`

Pendente:

- definir fluxo oficial entre DLQ relacional e DLQ em stream
- separar falhas retryable e terminais
- padronizar taxonomia de erro

### 4. Validacao de performance e memoria

Situacao real:

- a nova arquitetura reduz payload em fila por design

Pendente:

- anexar benchmark
- medir impacto real de memoria
- medir backlog e throughput em ambiente controlado

---

## Fluxo Atual Esperado

```text
1. ingest_batalhao.py
   -> cria missao
   -> registra politica
   -> envia URL para stream:ingestion

2. WorkerIntelligence
   -> classifica URL
   -> despacha para L0, L12 ou L34

3. Executor
   -> captura conteudo
   -> gera capture_id
   -> salva bruto em data/raw/
   -> emite evento em stream:captured_raw

4. CaptureControlWorker
   -> registra captura no PostgreSQL
   -> envia referencia para stream:dataclear

5. WorkerDataClear
   -> le raw_uri
   -> aplica DataClear
   -> grava dataset curado
```

---

## Estrutura Atual dos Artefatos

### Raw Store

Local atual:

`data/raw/YYYY/MM/DD/{mission_id}/`

Conteudo esperado:

- `{capture_id}.html`
- `{capture_id}.meta.json`

### Curated Store

Local alvo ja refletido no codigo:

`data/curated/YYYY/MM/DD/{mission_id}/dataset.jsonl`

Observacao:

- esse contrato ja deve orientar o codigo novo
- o compose e os volumes ainda precisam ser alinhados para refletir esse caminho como padrao operacional

---

## Exemplo de Registro Curado

```json
{
  "id_hash": "...",
  "url": "https://...",
  "capture_id": "uuid-v4",
  "mission_id": "uuid-v4",
  "fidelity_score": 0.85,
  "data": {
    "title": "...",
    "markdown_body": "...",
    "semantic_chunks": []
  }
}
```

---

## O que o Squad Deve Assumir Como Verdade

### Verdades que ja podem guiar implementacao

- esta branch nao e mais de RAG
- o contrato correto e orientado a artefato
- executores devem persistir bruto antes da curadoria
- DataClear deve consumir `raw_uri`
- `capture_id` e `mission_id` sao parte obrigatoria da linhagem

### Verdades que ainda exigem consolidacao

- PostgreSQL como dependencia obrigatoria de runtime
- deploy oficial completo da nova arquitetura
- DLQ final unificada e observabilidade de producao
- metricas que provem ganho operacional

---

## Proximos Passos Recomendados

1. alinhar `docker-compose.yml` com a nova arquitetura
2. subir PostgreSQL como dependencia oficial
3. revisar volumes para `data/raw` e `data/curated`
4. consolidar o papel do `CaptureControlWorker` no deploy
5. fechar politica de DLQ e retry
6. adicionar validacao objetiva de throughput, backlog e memoria

---

## Conclusao

O Grande Desacoplamento ja aconteceu no nivel de direcao arquitetural e em parte importante do codigo.

O que ainda falta nao e redefinir a visao. O que falta e fechar a operacao:

- infraestrutura
- catalogo em runtime
- deploy coerente
- evidencias de performance
- governanca de falha

Leitura final para o squad:

- tratem esta arquitetura como `nova base oficial`
- tratem o deploy atual como `em transicao`
- nao recoloquem responsabilidades de RAG nesta branch
