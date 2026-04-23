# Plano de Refatoração: Sincronicidade Honesta e Heurística de Poda (DataClear)

Este plano corrige o bug massivo onde o frontend exibia falso-positivo de ingestão (criando coleções ilusórias) quando a raspagem resultava em textos vazios devido a armadilhas de "Honeypots" criadas por SPAs/Plugins.

## Mudanças Executadas

### 🪚 `core/stages/dataclear.py` (Resiliência de Extração)
A armadilha consistia em encontrar o container `<div role="main">` injetado por plugins de acessibilidade completamente sem conteúdo, levando a poda rígida a descartar todo o blog.
- Implementamos **Heurística de Fallback Cascata:** 
  1. `<main>`
  2. `[role="main"]`
  3. `<article>`
- Adicionamos **Validação de Densidade:** Se um destes containers for encontrado mas o seu texto puro (`get_text`) contiver menos de 200 caracteres, a busca ignora-o e passa para o fallback até cair no `<body>` original.

### 🛡️ `rag_generator.py` (Contrato de Confiança Frontend/Backend)
- O executor `run_neural_sync` agora recupera o status real de `ingest_dataset_file`.
- Caso seja vazio (0 chunks), ele aborta o motor disparando `Raise ValueError('Site Vazio ou Blindado...')`.
- O endpoint da API `/ingest/url` captura o ValueError e despacha como um `HTTP 400 Bad Request` nativo, que será capturado pela nossa UI em `index.html`.

---
## 🛠️ Execution Telemetry (Histórico de Execução)

Abaixo constam os dados desta intervenção para escalar nas camadas do Nosso Pipeline de Dados Táticos:

*   **1. Worked (Área de Atuação):** NLP Poda Semântica e Orquestração HTTP Error Handling.
*   **2. Task Geral:** Dataclear Honeypot Escape & True Sync State.
*   **3. Cleanup & Automation:** 
    *   Arquivamento deste registro histórico para alimentação de pipeline.
*   **4. Write (Geração Curada):** 
    *   `plan/implementation_plan_rag_dataclear_v3.md`
    *   `task.md` (Controle ativado)
*   **5. Refactor (Código Modificado):**
    *   `core/stages/dataclear.py`: Lógica do Array "candidates" iterável por tamanho `> 200`.
    *   `rag_generator.py`: Throw Exception em `run_neural_sync` -> Erro 400 no endpoint `/ingest/url`.
*   **6. Commands (Terminal executado):**
    *   `docker exec neuralsafety_engine python -c "..."` (4 Injeções Diagnósticas Físicas)
*   **7. Files Modified:**
    *   `core/stages/dataclear.py`
    *   `rag_generator.py`
