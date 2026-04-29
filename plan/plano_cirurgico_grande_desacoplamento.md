# Plano Cirurgico por Fase - Grande Desacoplamento

## Objetivo Executivo

Executar a refatoracao da branch atual para transforma-la em uma plataforma exclusiva de `Crawler Massivo + DataClear`, sem quebrar a operacao ja existente de forma abrupta.

Diretriz principal:

- remover completamente o dominio de RAG desta branch
- introduzir persistencia bruta obrigatoria
- desacoplar a curadoria do fluxo de captura
- formalizar governanca, catalogo e observabilidade

---

## Principios de Execucao

- nenhuma fase deve depender de reescrita total
- cada fase precisa deixar o sistema operacional
- contratos devem mudar antes de otimizacoes
- qualquer transicao deve preservar replay e rollback
- o time deve priorizar `artifact-oriented architecture`

---

## Fase 1 - Purificacao de Dominio

### Objetivo

Separar definitivamente o dominio `crawler/data platform` do dominio `RAG/serving`.

### Escopo

- remover FastAPI e endpoints de RAG
- remover memoria conversacional
- remover vetorizacao e ChromaDB
- remover fluxo de ingestao semantica local
- atualizar documentacao e compose para refletir somente crawler e curadoria

### Mudancas esperadas

#### Codigo

- remover `rag_generator.py`
- remover `core/rag_service.py`
- remover `core/ingestor.py`
- remover `core/memory_manager.py`
- remover referencias a UI RAG em `static/`

#### Dependencias

- retirar `chromadb`
- retirar `openai`
- retirar `fastapi`
- retirar `uvicorn`
- retirar `tiktoken`
- retirar `python-multipart`

#### Documentacao

- reescrever `LEIA-ME.md`
- revisar `docker-compose.yml`
- revisar docs que descrevem o projeto como RAG

### Critérios de pronto

- o repositorio sobe sem dependencias de RAG
- nenhum fluxo principal depende de OpenAI
- a narrativa oficial do repositorio e `Capture & Curation Plane`

### Riscos

- remocao incompleta deixar imports mortos
- documentacao desatualizada confundir o time
- testes antigos continuarem refletindo o dominio anterior

---

## Fase 2 - Introducao do Raw Capture Plane

### Objetivo

Persistir o material bruto antes de qualquer limpeza.

### Escopo

- criar camada de storage bruto
- salvar HTML/JSON bruto e metadados por captura
- parar de enviar `html_content` bruto pela fila
- publicar apenas referencias para artefatos brutos

### Mudancas esperadas

#### Novos componentes

- `RawArtifactWriter`
- `RawArtifactReader`
- schema de `capture metadata`

#### Mudancas nos executores

- `ExecutorL0`
- `ExecutorL12`
- `ExecutorL34`

Cada executor deve:

- capturar o conteudo
- persistir o bruto
- gerar `capture_id`
- gerar `content_hash`
- emitir evento com `raw_uri`

#### Mudancas no broker

- criar `stream:captured_raw`
- adaptar `stream:dataclear` para receber referencias

### Contrato minimo da captura

```json
{
  "capture_id": "uuid",
  "mission_id": "uuid",
  "job_id": "cliente_alpha_001",
  "url": "https://dominio.com/pagina",
  "raw_uri": "file://... ou s3://...",
  "metadata_uri": "file://... ou s3://...",
  "executor_level": "L0-aiohttp",
  "http_status": "200",
  "captured_at": "timestamp",
  "content_hash": "sha256..."
}
```

### Critérios de pronto

- nenhum executor envia HTML inline para o DataClear
- toda captura valida gera artefato bruto persistido
- uma falha no DataClear nao exige novo fetch web

### Riscos

- path design ruim no storage
- metadados incompletos inviabilizarem replay
- fila antiga coexistir com contrato novo por tempo excessivo

---

## Fase 3 - Desacoplamento do DataClear

### Objetivo

Transformar o DataClear em worker realmente independente, consumidor de artefatos brutos.

### Escopo

- DataClear deixa de depender de `html_content` em memoria
- DataClear passa a ler do `raw_uri`
- DataClear registra execucao e resultado
- reprocessamento offline passa a ser suportado

### Mudancas esperadas

#### Novos comportamentos

- `WorkerDataClear` consome referencia de captura
- `run_dataclear_job` recebe conteudo carregado do Raw Store
- `DataLakeWriter` passa a operar com vinculacao a `capture_id` e `mission_id`

#### Reprocessamento

Criar fluxo para:

- reexecutar curadoria por `capture_id`
- reexecutar curadoria por `mission_id`
- aplicar nova `rule_version` sobre capturas antigas

### Critérios de pronto

- DataClear consegue processar a partir de `raw_uri`
- DataClear pode ser rerodado sem tocar na internet
- backlog de curadoria fica separado do backlog de captura

### Riscos

- reader de storage ficar acoplado ao tipo de backend
- reprocessamento sem versionamento de regra gerar confusao
- curadoria gravar saida sem vinculo forte com captura

---

## Fase 4 - Catalogo e Governanca

### Objetivo

Tirar do Redis o estado persistente de longo prazo e formalizar o catalogo operacional em PostgreSQL.

### Escopo

- criar schema relacional minimo
- registrar missao, politica, captura, curadoria e artefato
- permitir auditoria e rastreabilidade completas

### Entidades minimas

- `missions`
- `mission_policies`
- `captures`
- `curation_runs`
- `curated_artifacts`
- `dead_letters`

### Perguntas que o sistema deve responder

- qual missao gerou este dataset?
- quantas URLs entraram e quantas viraram captura valida?
- qual executor capturou cada origem?
- qual regra de curadoria gerou este artefato?
- quais URLs falharam de forma terminal?

### Critérios de pronto

- cada missao tem identificador persistente
- cada captura tem trilha completa
- cada JSONL homologado aponta para sua origem
- Redis deixa de ser catalogo implicito

### Riscos

- criar banco sem disciplina de escrita transacional
- duplicar verdade entre PostgreSQL e Redis
- popular catalogo so parcialmente

---

## Fase 5 - DLQ Real e Politicas de Retry

### Objetivo

Classificar falhas operacionalmente e tornar reprocessamento previsivel.

### Escopo

- separar falha retryable de falha terminal
- registrar motivo estruturado
- definir politicas por tipo de erro

### Categorias iniciais

- `NETWORK_TIMEOUT`
- `ROBOTS_DISALLOWED`
- `WAF_BLOCKED_PERSISTENT`
- `RAW_STORAGE_WRITE_FAILED`
- `RAW_ARTIFACT_MISSING`
- `DATACLEAR_PARSE_FAILED`
- `DATACLEAR_EMPTY_OUTPUT`
- `POLICY_VIOLATION`

### Comportamento desejado

- timeout: retry com limite e backoff
- falha de storage: retry prioritario
- robots negado: terminal
- WAF persistente: terminal ou fila especializada
- falha de curadoria: replay local via raw

### Critérios de pronto

- toda falha relevante recebe classificacao
- existe separacao entre DLQ terminal e recuperavel
- o time consegue operar retries de forma objetiva

### Riscos

- manter falhas genericas demais
- retry cego aumentar custo de proxy
- DLQ sem catalogo virar deposito opaco

---

## Fase 6 - Observabilidade Operacional

### Objetivo

Sair de observacao por logs e entrar em operacao por metricas.

### Escopo

- medir throughput, latencia, backlog e falha
- medir custo e bloqueio por camada
- gerar visibilidade por missao e dominio

### Indicadores minimos

#### Captura

- throughput por executor
- taxa de sucesso por executor
- taxa de escalonamento L0 -> L12 -> L34
- latencia media por dominio
- distribuicao de status HTTP

#### Curadoria

- backlog em `stream:dataclear`
- tempo medio por captura
- taxa de descarte por fidelidade
- falhas por `rule_version`

#### Missao

- URLs de entrada
- URLs deduplicadas
- capturas validas
- curados homologados
- custo estimado por executor

### Critérios de pronto

- o time consegue localizar gargalo por fase
- o time consegue medir custo e eficiencia de missao
- o time consegue distinguir problema de rede, defesa, storage e curadoria

### Riscos

- logs continuarem sendo unica fonte de verdade
- metricas sem cardinalidade util
- ausencia de correlacao entre missao, captura e erro

---

## Ordem Tecnica Recomendada

1. Purificar dominio
2. Introduzir Raw Capture Plane
3. Desacoplar DataClear
4. Criar catalogo em PostgreSQL
5. Formalizar DLQ e retries
6. Consolidar observabilidade

Motivo:

- remover RAG simplifica o repositorio
- storage bruto muda o contrato central
- DataClear desacoplado habilita replay
- catalogo consolida governanca
- DLQ e metricas amadurecem a operacao

---

## Checklists por Time

### Time Core

- remover dominio RAG
- ajustar imports e dependencias
- manter `main_batalhao` operacional

### Time Capture

- implementar `capture_id`
- persistir bruto
- emitir evento por referencia

### Time Curation

- ler do `raw_uri`
- versionar `rule_version`
- garantir replay offline

### Time Platform

- modelar PostgreSQL
- criar catalogo operacional
- estruturar DLQ e metricas

---

## Definition of Done por Programa

O programa sera considerado concluido quando:

- esta branch nao contiver mais responsabilidades de RAG
- o output bruto existir antes da curadoria
- o output curado for reproduzivel sem novo crawl
- o estado persistente principal estiver em PostgreSQL
- a operacao puder medir throughput, falhas, backlog e custo
- o unico produto desta branch for artefato bruto e artefato curado

---

## Resultado Esperado

Ao final da refatoracao, esta branch passara a ser:

- resiliente para captura massiva
- auditavel
- reprocessavel
- orientada a artefato
- governada por catalogo
- pronta para servir outros consumidores, incluindo um repositorio separado de RAG
