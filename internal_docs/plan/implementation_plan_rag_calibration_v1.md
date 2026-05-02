# Plano de Calibragem RAG e Sincronia de Dados

Este plano corrige a regressão cognitiva do Motor RAG, reestrutura o fluxo de dados assíncronos da interface e resolve a ambiguidade visual de diretórios.

## Mudanças Propostas

### 🧠 Ajuste Cognitivo (RAG Service)
- Refazer o `system_prompt` para afrouxar a punição sintática e focar apenas na **Grounded Truth (verdade documental)**, instruindo o LLM a atuar como um Engenheiro de Dados Sênior: formatação rica (Markdown, tabelas, tópicos) para substituir pensamento humano/produtividade.

### 🔄 Orquestração do Frontend & Backend
- Alterar o endpoint `/ingest/url` em `rag_generator.py` para aguardar a sincronização completa (Scraper + ChromaDB) antes de responder com sucesso ao cliente.
- O Spinner (🌀) da interface (`index.html`) ficará girando até o servidor disparar HTTP 200 Final, e o `<select>` só injetará a opção após o a certeza total.

### 🧹 Limpeza Estrutural
- Remover pastas fósseis da era CLI (`vector_db\` e `output\`) da raiz.

---

## 🛠️ Execution Telemetry (Histórico de Execução)

Abaixo estão registrados os dados de engenharia aplicados fisicamente ao projeto durante esta fase:

*   **1. Worked (Área de Atuação):** Sincronização Assíncrona e Alívio Cognitivo LLM.
*   **2. Task Geral:** Calibragem RAG e Orquestração UI/Server.
*   **3. Cleanup & Automation:** 
    *   Deleção forçada via Powershell de `./vector_db` e `./output` (Diretórios obsoletos CLI).
    *   Criação arquitetônica do diretório `./plan/` para arquivamento histórico.
*   **4. Write (Geração Curada):** 
    *   `plan/implementation_plan_rag_calibration_v1.md`
*   **5. Refactor (Código Modificado):**
    *   `core/rag_service.py`: Reescrevemos o `system_prompt` para atuar como Engenheiro de Dados.
    *   `rag_generator.py`: Refatoramos `/ingest/url` e implementamos `asyncio.to_thread` para travar o sinal HTTP 200 até a gravação total do ChromaDB.
    *   `static/index.html`: Refatoramos o botão `#sync-btn` para bloquear o clique e refletir apenas sucesso verídico da rede.
*   **6. Commands (Terminal executado):**
    *   `Remove-Item -Path "vector_db", "output" -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force -Path "plan";`
    *   `docker-compose up -d --build`
*   **7. Files Modified:**
    *   `core/rag_service.py`
    *   `rag_generator.py`
    *   `static/index.html`
