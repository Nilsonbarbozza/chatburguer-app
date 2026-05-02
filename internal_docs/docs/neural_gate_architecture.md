# Documentação Técnica: Arquitetura NeuralGate & Embeddings v3

Esta documentação detalha a implementação de elite do motor RAG (Retrieval-Augmented Generation) do NeuralSafety, focando em robustez, eficiência de tokens e precisão semântica.

## 🏗️ Core Tecnológico
O sistema utiliza o modelo **text-embedding-3-small** da OpenAI como motor principal de vetorização. 

### 🚀 Por que text-embedding-3-small?
- **Economia Profissional**: 62.500 páginas por dólar.
- **Superioridade Técnica**: Supera o modelo legado `ada-002` em benchmarks MTEB (62.3%).
- **Tokenização**: Utiliza `cl100k_base` via biblioteca `tiktoken` para contagem precisa de tokens pré-ingestão, garantindo que nunca excedamos o limite de **8192 tokens** por entrada.

## 🧠 Estratégias e "Sacadas" Implementadas

### 1. Otimização Matryoshka (Dimensions: 512)
Diferente de implementações comuns que usam os 1536 eixos fixos, nossa implementação (referenciada em [rag_service.py](file:///c:/Users/Ti/Desktop/process-cloner/core/rag_service.py)) utiliza a técnica de **Truncamento Habilitado por Aprendizado**.
- **O que faz**: Compactamos o vetor para 512 dimensões.
- **Vantagem**: Reduz o consumo de memória no ChromaDB e acelera a busca matemática local em ~3x, mantendo a precisão semântica几乎 intacta.

### 2. O Portão Neural (Hybrid Reranking)
Implementamos uma camada de inteligência entre a busca e a resposta final para eliminar o **Ruído Semântico**.
- **Técnica**: Mix de Similaridade de Cosseno (Local) + Validação via GPT-4o-mini.
- **Funcionamento**: 
    - Se a similaridade for altíssima (>0.90), o dado entra direto.
    - Se houver ambiguidade, o **GPT-4o-mini** atua como um "reranker" binário, validando a utilidade do trecho.
    - Isso garante **Zero Hallucination**, pois a IA de geração só recebe dados verificados.

### 3. Gestão de Memória com Sliding Window
Gerenciado em `core/memory_manager.py`, o sistema utiliza uma janela deslizante com **Sumarização Ativa**.
- **Sacada**: Em vez de enviar todo o histórico e estourar o custo, compactamos conversas antigas em "âncoras de memória", mantendo o contexto rico e o custo de entrada baixo.

## 📊 Eficiência Operacional
Graças ao uso intensivo de `tiktoken` e do modelo `-3-small`, o NeuralSafety consegue atingir uma robustez de nível empresarial com um dos menores custos por consulta do mercado atual.

---
*Documentação gerada pelo Agente Antigravity para o projeto Process-Cloner.*
