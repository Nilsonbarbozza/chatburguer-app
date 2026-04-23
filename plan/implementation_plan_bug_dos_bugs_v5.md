# Memorial de Guerra: O "Bug dos Bugs" e a Sincronicidade Neural

Este documento registra a resolução da instabilidade crítica que impedia o funcionamento do NeuralSafety RAG em ambiente Docker, servindo como base técnica para futuras expansões.

## 🕵️‍♂️ O Diagnóstico: A Cápsula do Tempo
O sistema apresentava um comportamento esquizofrênico onde o **Ingestor** (Scraping) dizia ter sucesso, mas o **Agente de Chat** não encontrava os dados.

### As 3 Camadas da Falha:
1.  **Isolamento de Código (A Raiz):** O `docker-compose.yml` original não mapeava a pasta de código (`./core`, `./rag_generator.py`). O Docker estava rodando uma versão "assada" e antiga dos arquivos. Minhas correções no Windows não chegavam ao "cérebro" do container.
2.  **A Armadilha do Honeypot:** O Agente de Limpeza (`dataclear.py`) estava sendo enganado por tags de acessibilidade vazias (`role="main"`), apagando 100% do texto capturado por acreditar que o site estava vazio.
3.  **A Crise de Identidade do ChromaDB:** O banco de dados estava sendo criado na memória volátil do container (`/app/vector_db`) enquanto o sistema esperava lê-lo no volume persistente (`/app/data/vector_db`). Ao reiniciar, o conhecimento "morria".

## 🛠️ A Solucionabilidade (Engenharia de Elite)

### 1. Sincronização em Tempo Real (`docker-compose.yml`)
Implementamos o mapeamento de volume total (`.:/app`). Agora, qualquer mudança feita no código fonte é instantaneamente refletida no motor Docker, eliminando a "Cápsula do Tempo".

### 2. Heurística de Densidade Cascata (`core/stages/dataclear.py`)
Ensinamos ao robô que "nome de tag não é documento". Ele agora busca o conteúdo principal em uma cascata:
-   Procura `post-content` (Foco em Blogs).
-   Valida se o bloco tem **mais de 200 caracteres**.
-   Se for um "Honeypot" (vazio), ele ignora e busca o próximo candidato até chegar ao Body.

### 3. Unificação de Caminhos Absolutos (`core/rag_service.py`)
Forçamos o uso de caminhos absolutos via `os.path.abspath(os.getenv("CHROMA_DB_PATH"))`. Isso garante que tanto quem escreve os vetores quanto quem os lê, estejam batendo na mesma porta do disco rígido.

---

## 🛠️ Execution Telemetry (Debriefing Final)

*   **1. Worked (Área de Atuação):** DevOps, NLP Refinement, Vector DB Orchestration.
*   **2. Task:** Calibração de Motor RAG Enterprise e Resiliência Docker.
*   **3. Cleanup & Automation:** 
    *   Remoção de logs de debug e normalização de caminhos.
    *   Criação desta documentação de "Lessons Learned".
*   **4. Write (Arquivos Criados/Garantidos):** 
    *   `plan/implementation_plan_bug_dos_bugs_v5.md`
    *   `hack/waf_evasion_architecture.md`
*   **5. Refactor (Código Modificado):**
    *   `docker-compose.yml`: Mapeamento de volume bidirecional.
    *   `core/config.py`: Centralização de OUTPUT para `data/output`.
    *   `core/stages/dataclear.py`: Sniper de conteúdo útil (Anti-Honeypot).
    *   `core/rag_service.py`: Correção de assinatura e caminhos absolutos.
*   **6. Commands (Arsenal Utilizado):**
    *   `docker-compose up -d --build` (O Reinício da Era Docker).
    *   `Invoke-RestMethod` (Testes balísticos de URL).
    *   `chromadb.peek()` (Auditoria forense de vetores).
*   **7. Files Modified:**
    *   `docker-compose.yml`, `.env`, `core/config.py`, `core/stages/dataclear.py`, `core/rag_service.py`, `core/ingestor.py`.

---
> [!TIP]
> O sistema agora é agnóstico à complexidade do site. Se houver texto, nós o encontraremos. Se houver defesa, nós a contornaremos.
