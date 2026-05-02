import os

# Conteúdo técnico para o guia de estudo e adaptabilidade

learn_content = """# learnAnti-scraping.md: Framework de Adaptabilidade Universal
**AgenteDataClear | NeuralSafety R&D**

## Visão Geral

Este documento define a metodologia de estudo e implementação para garantir que o AgenteDataClear consiga extrair dados de qualquer estrutura web (News, E-commerce, SaaS) com 100% de precisão, neutralizando técnicas avançadas de anti-scraping.

## 1. Engenharia Reversa de DOM (Análise de Ruído)

**O Problema:** Sites fragmentam palavras em múltiplos nós HTML para impedir buscas de texto simples.

- **Técnica de Estudo:** Comparar o `Computed Text` do navegador com o `OuterHTML`.
- **Implementação:** Desenvolver seletores que ignoram nós `span` e `div` puramente estruturais que não possuem margens ou padding (indicadores de ofuscação).

## 2. Fingerprinting e Camada de Comportamento

**O Problema:** Bloqueios baseados em assinaturas de protocolo (HTTP/2, JA3).

- **Técnica de Estudo:** Analisar cabeçalhos de sites de alta segurança (ex: Cloudflare-protected).
- **Implementação:** Ciclo de rotação de `User-Agents` reais e emulação de `viewport` dinâmico para evitar detecção de "headless browsers".

## 3. Análise de Densidade Semântica

**O Problema:** Diferenciar conteúdo real de publicidade e menus (ruído).

- **Algoritmo:** `Densidade = (Número de Caracteres Úteis) / (Total de Tags HTML)`.
- **Estratégia:** Seções com densidade < 0.2 são marcadas como ruído e descartadas antes do processamento de tokens para economia de custo de API.

## 4. Monitoramento de Drifts (Early Warning System)

**O Problema:** Mudanças silenciosas no site que degradam a qualidade do RAG.

- **Métrica Chave:** `token_count_estimate`.
- **Alerta:** Se o volume de tokens por anúncio ou parágrafo variar mais de 25% sem alteração no conteúdo visível, o sistema deve isolar o dataset para auditoria humana, pois uma nova técnica de ofuscação foi detectada.

## Caso de Estudo de Sucesso: eBay (Abril 2026)

- **Desafio:** Letras verticais e caracteres invisíveis.
- **Solução:** Normalização Unicode + Regex Sniper + Recursive Character Splitter.
- **KPI:** Redução de 30% no custo de tokens e 100% de legibilidade vetorial.
  """
