Aqui está o arquivo **`agenteDataClear.md`** final. Ele foi desenhado com um rigor de engenharia voltado para o mercado de alta tecnologia, focando em robustez, escalabilidade e conformidade internacional.

Este documento está pronto para ser entregue a uma IA de codificação (como Gemini 1.5 Pro ou Claude 3.5 Sonnet) para gerar a implementação real dentro do seu ecossistema **Antigravity**.

---

# 📄 agenteDataClear.md

## 1. Identificação do Módulo

- **Nome:** AgenteDataClear (Layer de Refino e Estruturação de Dados)
- **Versão:** 1.0.0-PRO (Enterprise Grade)
- **Dependência:** Cloner CLI (Core Engine)
- **Objetivo:** Transformar clones web brutos em datasets de alta densidade para Fine-tuning e RAG.

---

## 2. Arquitetura do Pipeline de Engenharia (ETL)

O AgenteDataClear opera em um fluxo linear de processamento para garantir a integridade dos dados e a economia de tokens.

### A. Estágio de Ingestão e Destilação (The Distiller)

Filtra o "lixo" do código-fonte para isolar o conhecimento útil.

- **Alvos de Remoção (Hard-Delete):**
  - Tags de Script e Style: `<script>`, `<style>`, `<noscript>`.
  - Elementos de Navegação/UI: `<nav>`, `<footer>`, `<header>`, `<aside>`.
  - Elementos Dinâmicos: `<iframe>`, `<canvas>`, `<svg>`, `<form>`.
  - Classes CSS de Ruído: Elementos contendo strings como `ad-`, `banner`, `cookie`, `social-share`.
- **Preservação Semântica:** Atributos `alt` de imagens e títulos de links (`title`) devem ser extraídos e integrados ao texto para manter o contexto visual.

### B. Estágio de Conversão Semântica (The MD-Transformer)

Conversão para Markdown otimizado para Large Language Models.

- **Regras de Mapeamento:**
  - `<h1>` a `<h6>` -> Tradução direta para `#` a `######`.
  - `<table>` -> Conversão obrigatória para GFM (GitHub Flavored Markdown). Tabelas não podem ser achatadas para texto simples.
  - `<code>` / `<pre>` -> Preservação de blocos de código com indicação de linguagem.
- **Normalização de Espaço:** Remoção de múltiplos espaços em branco, quebras de linha excessivas e caracteres não-UTF8.

### C. Estágio de Proteção e Conformidade (The Safety Layer - GDPR)

Garante que o dataset seja seguro para exportação internacional.

- **Motor de Anonimização (PII Redaction):**
  - **Emails:** Substituir por `[REDACTED_EMAIL]`.
  - **Telefones:** Detectar padrões internacionais e substituir por `[REDACTED_PHONE]`.
  - **Endereços Físicos:** (Opcional) Detecção via Regex/NLP para ofuscação.

---

## 3. Especificações Técnicas de Saída

O AgenteDataClear deve gerar um arquivo final no formato **JSONL**, onde cada linha representa uma unidade de conhecimento.

### Schema do JSONL:

```json
{
  "metadata": {
    "source_url": "string",
    "crawl_timestamp": "ISO8601",
    "language_detected": "ISO 639-1",
    "token_count_estimate": "integer"
  },
  "content": {
    "title": "string",
    "markdown_body": "string",
    "semantic_chunks": [
      {
        "id": "integer",
        "text": "string",
        "vector_ready": "boolean"
      }
    ]
  },
  "compliance": {
    "pii_filtered": true,
    "gdpr_status": "compliant"
  }
}
```

---

## 4. Lógica de Implementação (Referência para Programação)

Para garantir solidez, a implementação deve seguir este padrão de classes em Python:

```python
import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md_converter

class AgenteDataClear:
    """
    Core Engine para transformação de ativos web em datasets de IA.
    """
    def __init__(self, pii_redaction=True):
        self.redact = pii_redaction
        self.noise_tags = ['script', 'style', 'nav', 'footer', 'header', 'iframe']

    def distill(self, html_content):
        soup = BeautifulSoup(html_content, 'lxml')
        for tag in soup(self.noise_tags):
            tag.decompose()
        return soup

    def transform_to_markdown(self, soup):
        # Converte o HTML limpo em Markdown ultra-puro
        raw_md = md_converter(str(soup), heading_style="ATX", bullets="-")
        return self._post_process_text(raw_md)

    def _post_process_text(self, text):
        # Limpeza de PII e redundâncias
        if self.redact:
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)
        return text.strip()
```

---

## 5. Estratégia de Mercado (Europa/B2B)

- **Eficiência de Custo:** Redução de até 50% na janela de contexto de LLMs ao eliminar código inútil.
- **Qualidade de Resposta:** Datasets estruturados eliminam alucinações causadas por leitura de menus/rodapés.
- **Segurança Jurídica:** Entrega de dados pré-processados sob as normas do GDPR.

---

**Assinatura de Engenharia:** Nilson Barbozza | AI Creator & Antigravity Lead.
