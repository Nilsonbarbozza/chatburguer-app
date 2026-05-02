# Raio-X de Transição: RAG Motor ➔ Crawler de Batalhão

Este documento define o mapeamento exato do abismo entre o que nosso sistema faz hoje, e o que ele vai fazer amanhã, detalhando onde a "Faca" da refatoração vai atuar.

---

## 1. O Estado Atual da Nossa Infraestrutura
Hoje, o nosso motor (`neuralsafety_engine`) roda através do **FastAPI** (`rag_generator.py`). Ele é monolítico e altamente resiliente no que se propõe.

**Como funciona hoje (Modo Sniper):**
1. Você envia UMA url via endpoint POST /ingest/url.
2. O servidor bloqueia até terminar a execução.
3. O `core/stages/scraper.py` (usando Playwright via de regra) puxa o HTML.
4. O `dataclear.py` lapida e tira PII.
5. O `ingestor.py` faz vetorização via OpenAI Embeddings e grava no ChromaDB.

*Apesar de o motor PII provar ser fortíssimo, este pipeline sequencial quebra se fornecermos 10.000 URLs*. Ficaríamos aguardando o endpoint por anos, além de pagar o custo caríssimo de Playwright para todas elas.

---

## 2. A Nova Arquitetura (Modo Metralhadora Distribuída)
O novo modelo vira a arquitetura de ponta a cabeça: adotaremos um modelo Event-Driven. As URLs não bloqueiam mais a API. Elas são cuspidas num **Message Broker (Redis Streams)**. Vários robôs invisíveis (**Workers**) puxam essas URLs em paralelo, cada um com uma classe de arma (`aiohttp`, `curl_cffi`, `playwright`). E ao invés de jogar no RAG obrigatoriamente, despejam nos HDs em `JSONL` e `Parquet`.

### Novas Bibliotecas Necessárias (`requirements.txt`)
- `redis` e `redis.asyncio`
- `curl_cffi` (Para o Executor Nível 1/2 TLS Spoofing)
- `pyarrow` (Para conversão do dataset em Parquet no final)

---

## 3. Mapa de Refatoração e Cortes Cirúrgicos

Para instalar o "*Motor de Guerra*", precisaremos mexer em arquivos existentes sem quebrar o que já funciona no RAG.

### 🟡 Alterações / Refatorações (Arquivos Existentes)

1. **`docker-compose.yml` e `.env`**
   - **O que faremos:** Precisamos injetar um container do **Redis** para ser o nosso sistema nervoso central do broker e cache de classificação.
2. **`core/stages/dataclear.py`**
   - **O que faremos:** Adaptaremos a classe de limpeza para operar como o portão universal de saída e obrigaremos o preenchimento do **Schema Canônico Universal** (id_hash, timestamp, url, executor) para todo dado extraído. Ele não vai processar mais *apenas* para ChromaDB, vai emitir um Dicionário Universal preparado pro Data Lake.
3. **`rag_generator.py` (API)**
   - **O que faremos:** Criaremos um novo end-point: `/batalhao/ingest`. Em vez de fazer scraping sincrono, ele apenas injeta o bulk de urls no Redis Stream de Ingestão e retorna STATUS 200 ("URLs na esteira").

### 🟢 Novas Criações (As Peças do Motor)

1. **`core/mq/` (Message Queue Namespace)**
   - `redis_manager.py`: O coração que gerencia prioridade e deduplicação no Redis.
   - `worker_base.py`: O consumidor genérico que roda nos containers e lida com leitura `XREADGROUP` e confirmações `XACK`.
2. **`core/defense/intelligence.py`**
   - O radar de WAFs (Camada 3.2 do Doc). Vai bater no site rapidamente com requisição barata e classificar entre Níveis (0 a 4).
3. **`core/executors/` (A Cavalaria)**
   - `executor_l0_aiohttp.py`: Velocidade extrema pra sites sem bloqueio.
   - `executor_l12_curlcffi.py`: TLS spoofing pesado que imita comportamento Chrome nativo na rede.
   - *(A ser refatorado futuramente para pool):* `executor_l34_playwright.py`.
4. **`core/export/` (Entregáveis e Formatos)**
   - `data_lake_writer.py`: Coleta o dicionário normalizado pelo `dataclear.py`, salva append no arquivo `JSONL`, gera logs e eventualmente ativa o motor de `Parquet`.

---

## O Veredito de Viabilidade
Sua base em `process-cloner` e o seu motor de limpeza (`dataclear.py`) estão com resiliencia total. O desafio da Branch `crowler` será construir a fila do zero sem impactar as funções nativas de Clonagem Front-end do Cloner. O caminho é limpo e favorável.🚀
