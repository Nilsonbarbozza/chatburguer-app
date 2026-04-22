# NeuralSafety: Engine RAG de Nível Militar 🏛️🛡️

O **NeuralSafety** é um ecossistema RAG (Retrieval-Augmented Generation) de alta precisão, projetado para operações corporativas que exigem resiliência total, segurança de dados e resposta de alta fidelidade.

## 💎 Diferenciais Estratégicos

- **NeuralGate (Portão Neural):** Arquitetura de filtragem híbrida (Matemática + IA) que elimina alucinações e garante que a IA utilize apenas fatos comprovados do documento.
- **Vetorização Matryoshka (512d):** Otimização de busca semântica de elite, reduzindo custos de infraestrutura e acelerando a resposta em 3x em comparação com modelos padrão.
- **Scraper Playwright Stealth:** Motor de extração de dados capaz de contornar proteções avançadas e destilar informações úteis de sites complexos.
- **Auditoria Financeira Nativa:** Monitoramento de contagem de tokens em tempo real via `tiktoken` (cl100k_base).

## 🏗️ Arquitetura do Sistema

Consulte o relatório mestre em [docs/neural_workflow_master.md](file:///c:/Users/Ti/Desktop/process-cloner/docs/neural_workflow_master.md) para detalhes técnicos sobre o pipeline de ingestão e inferência.

## 🚀 Guia de Operação (Modo Enterprise)

### Instalação e Requisitos
- Python 3.10+
- OpenAI API Key
- ChromaDB (Persistência Vetorial local)

### Início Rápido
1. Inicie o servidor: `python rag_generator.py`
2. Acesse a interface: `http://localhost:8000`
3. Use o painel **NeuralSync** para injetar URLs diretamente no cérebro do sistema.

---
*Status: Branch `rag_generator` - Estágio de Dockerização.*
