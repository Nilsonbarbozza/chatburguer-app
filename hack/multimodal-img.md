# Roadmap de Engenharia: Motor de Extração Multimodal (Vision)

**Projeto:** Cloner CLI - AgenteDataClear
**Status:** Planejamento Futuro (Pós-Validação do Text Engine)

## 1. Visão Geral (O "Ouro Puro" Multimodal)

O RAG tradicional é cego. Ele lê texto, mas perde o contexto de infográficos, fotos de produtos e diagramas. O objetivo deste módulo é garantir que o nosso pipeline entregue dados formatados perfeitamente para LLMs Multimodais.

A captura realizada na BBC provou que o conversor Markdown é capaz de preservar a relação semântica entre o texto e a imagem:
`![Estreito de Ormuz é uma das rotas de energia mais importantes do mundo](link)`

Ao manter essa estrutura dentro de um _Semantic Chunk_, o modelo de IA consegue associar o parágrafo atual à imagem correspondente, permitindo respostas incrivelmente ricas.

## 2. Níveis de Maturidade da Extração Visual

Para estruturarmos o desenvolvimento, o tratamento de imagens será dividido em três fases de engenharia:

### Nível 1: Preservação de Metadados (Atual/Base)

- **Técnica:** O parser varre o HTML em busca de tags `<img>`.
- **Ação:** Extrai os atributos `alt`, `title` e `src` e os converte para a sintaxe nativa do Markdown.
- **Vantagem:** Custo zero de processamento adicional e enriquecimento imediato do banco vetorial com descrições textuais das imagens.

### Nível 2: Limpeza de Assets de UI (Higiene Visual)

- **O Problema:** Portais de notícias e e-commerces estão cheios de imagens inúteis (ícones de redes sociais, logos minúsculos, setas de carrossel, pixels de rastreamento).
- **Ação:** Implementar no `dataclear.py` um filtro dimensional e heurístico.
- **Regras de Poda Visual:**
  - Deletar imagens no formato `.svg` (geralmente ícones estruturais).
  - Deletar imagens que não possuem atributo `alt` E `title`.
  - Se a classe da imagem contiver palavras como `icon`, `logo`, `tracker`, `avatar` -> _Decompose_.

### Nível 3: Visão Ativa e OCR (O Próximo Passo)

- **Ação:** Quando o crawler encontrar uma imagem vital (ex: um gráfico de finanças sem `alt-text` no site do cliente), o pipeline fará o download temporário da imagem para a memória.
- **Processamento:** Um modelo leve de visão computacional (ou uma chamada de API especializada) fará o OCR e a descrição do gráfico, injetando esse texto gerado de volta no Markdown original antes de enviar para o banco vetorial.

## 3. Impacto na Estratégia de Chunking

Quando o módulo Visual estiver ativo, o _Semantic Splitter_ precisará de uma nova regra:
**Regra de Coesão de Mídia:** Nunca quebrar um chunk separando uma tag `![imagem]()` do seu parágrafo adjacente. A imagem e a sua legenda descritiva devem sempre coabitar o mesmo vetor para garantir o contexto.

---

_Documento reservado para implementação na Fase 2 de P&D._
