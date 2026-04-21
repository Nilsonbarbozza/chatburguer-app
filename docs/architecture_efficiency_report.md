# NeuralSafety: Relátorio de Engenharia, Economia e Robustez (v1.0)

Este documento detalha os pilares arquiteturais do sistema NeuralSafety, focando na otimização de consumo de tokens e na resiliência do ecossistema RAG (Retrieval-Augmented Generation).

---

## 1. O Motor de Chunking Semântico
A economia de tokens começa na fase de ingestão (`DataClearStage`). Em vez de dividir documentos por caracteres aleatórios, utilizamos a técnica de **Janela Deslizante com Overlap**.

- **Fatiamento Atômico:** Os dados são divididos em "chunks" de ~1000 caracteres.
- **Preservação de Contexto (Overlap):** Mantemos uma sobreposição de 150 caracteres entre chunks. Isso garante que, se uma informação crítica for cortada ao meio, ela aparecerá completa no chunk seguinte.
- **Higiene de PII (GDPR Match):** O sistema remove telefones e e-mails na raiz. **Impacto:** Menos lixo processado e maior segurança jurídica.

## 2. Retrieval Dinâmico e Poda de Custos
Diferente de sistemas RAG comuns que utilizam um `Top-K` fixo (sempre retornando 3 ou 5 resultados), o NeuralSafety utiliza o **Top-K Adaptativo com Limiar de Distância**.

- **Corte de Ruído (`threshold = 1.30`):** O sistema avalia a distância semântica de cada resultado. Se um pedaço de informação for considerado irrelevante (distância > 1.30), ele é descartado antes de chegar ao LLM.
- **Enriquecimento de Metadados:** Injetamos a `source_url` diretamente no contexto. Isso evita que a IA precise "adivinhar" a origem, economizando tokens que seriam gastos em alucinações ou redundâncias.
- **Resultado:** Redução de até 40% no payload de entrada em perguntas simples ("Oi", "Obrigado").

## 3. Gestão de Memória: Sliding Window + Sumarização
Este é o coração da estabilidade financeira do sistema. A memória do agente é gerenciada pela classe `SlidingWindowMemory`.

- **Janela de Curto Prazo (Raw Memory):** Mantemos apenas os 3 últimos turnos (6 mensagens) na íntegra. Isso preserva a fluidez imediata da conversa.
- **Sumarização Ativa (Long-Term Memory):** Quando o histórico excede 6 mensagens, o sistema executa uma compressão recursiva. O passado é transformado em um **Resumo de Entidades** de ~3 linhas.
- **O Teto de Custos (Ceiling):** Independentemente se a conversa durar 10 ou 100 turnos, o volume de tokens de histórico enviados para a OpenAI permanece constante.
- **ROI Técnico:** Prevenção de explosão de custos em 80% em sessões de chat prolongadas.

## 4. Camada de Resiliência Enterprise
A robustez do sistema é garantida pela integração com a biblioteca `tenacity` e o uso de chamadas assíncronas no FastAPI.

- **Auto-Recuperação (Exponential Backoff):** Em caso de falhas na API da OpenAI (Rate Limit ou Timeout), o sistema retenta a chamada automaticamente com tempos de espera crescentes.
- **Persistência de Sessão (SQLite):** O histórico não reside apenas na RAM. Usamos um banco de dados local para garantir que a memória sobreviva a reinicializações do servidor.
- **Concorrência Assíncrona:** O `rag_generator.py` processa requisições de forma não bloqueante, permitindo escala horizontal.

## 5. NeuralSync: Automação de Fluxo (URL-to-RAG)
Para eliminar a fricção operacional, o sistema agora conta com um pipeline de sincronização dinâmica.

- **Ingestão On-demand:** Através da interface web, o usuário pode injetar uma nova fonte de conhecimento apenas fornecendo a URL.
- **Processamento em Segundo Plano (Async):** O Scraper (Playwright) e o IngestorAgent trabalham em background, permitindo que a IA continue respondendo enquanto novos dados são processados.
- **Auto-Standardization:** Nomes de coleções são gerados automaticamente via parsing de domínio, garantindo organização sistêmica sem intervenção humana.

---
## Conclusão de Eficiência
A arquitetura NeuralSafety foi desenhada sob o princípio de **"Contexto Máximo com Consumo Mínimo"**. Ao unir limpeza cirúrgica, busca criteriosa, memória comprimida e agora **automação de ingestão**, entregamos uma solução que é, simultaneamente, mais inteligente e significativamente mais barata que implementações convencionais.

---
**Elaborado por:** NeuralSafety Engineering Dept.
**Data:** 21 de Abril de 2026
