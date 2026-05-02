# Correção de Arquitetura: Persistência de Volume e Sincronia de Dados

Este plano corrige o erro de "Arquivos Fantasmas" onde os componentes de Scrape (Playwright) e Ingestão (ChromaDB) estavam olhando para caminhos diferentes dentro do container.

## Causa Raiz
O `core/config.py` estava fixado para gravar os resultados em `output/` na raiz do container. No Docker, essa pasta é volátil e separada do volume de dados persistente (`data/`). 
1. O Scraper gravava em `output/`.
2. O Ingestor tentava ler de `data/output/` (ou vice-versa dependendo do contexto).
3. O resultado era sempre um arquivo vazio sendo lido pelo Banco de Dados, gerando coleções nulas que sumiam no F5.

## Ação Corretiva
- **Update `core/config.py`**: Alterado `OUTPUT_DIR` padrão para `data/output/` garantindo que todos os assets (JSON, HTML, Chunks) caiam no volume persistente do Docker.
- **Backend Sync**: Refatorado `rag_generator.py` para reforçar caminhos absolutos e lançar `ValueError` (Erro 400 no front) se a leitura do volume falhar.

---

## 🛠️ Execution Telemetry (Histórico de Execução)

Abaixo constam os dados desta intervenção para abastecer o Pipeline:

*   **1. Worked (Área de Atuação):** Persistência de Dados e Orquestração de Volumes Docker.
*   **2. Task Geral:** Correção de Sync e Caminhos Voláteis.
*   **3. Cleanup & Automation:** 
    *   Gerado arquivamento histórico da correção em `plan/implementation_plan_persistence_fix_v4.md`.
*   **4. Write (Geração Curada):** 
    *   `plan/implementation_plan_persistence_fix_v4.md`
*   **5. Refactor (Código Modificado):**
    *   `core/config.py`: Alterado `OUTPUT_DIR` para `data/output`.
    *   `rag_generator.py`: Caminhos absolutos e tratamento de exceção semântica.
*   **6. Commands (Terminal executado):**
    *   `docker restart neuralsafety_engine`
*   **7. Files Modified:**
    *   `core/config.py`, `rag_generator.py`
