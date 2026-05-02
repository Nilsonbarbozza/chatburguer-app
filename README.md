# 🕸️ Agentic WebFetch API (B2B Enterprise)

O motor de extração e limpeza de dados mais resiliente e inteligente do mercado. Projetado para alimentar pipelines de RAG, Fine-tuning e Análise de Mercado com dados puros, sem ruído de UI e blindado contra WAFs.

## 🚀 Arquitetura Standalone
Esta API opera de forma independente, utilizando uma estrutura distribuída e assíncrona:
- **FastAPI**: Gateway de alta performance.
- **Redis**: Gestão de filas (ARQ) e Rate Limiting.
- **PostgreSQL**: Control Plane para missões e linhagem de dados.
- **Multi-Level Fetching**: Evasão de WAF em camadas (L0 a L34).

## 🛠️ Endpoints Principais

### 1. [POST] `/api/v1/fetch`
Extração direta de uma URL específica com limpeza "Gold Standard".
- **render_js**: Ativa Playwright para sites Single Page App.
- **force_stealth**: Ativa TLS Spoofing (Curl-cffi) para evitar bloqueios.

### 2. [POST] `/api/v1/search_and_fetch` (O Radar)
Busca inteligente na web, extração de múltiplas fontes e consolidação em Markdown único.
- Ideal para monitoramento de notícias e pesquisa de mercado em tempo real.

## 🐳 Como Levantar a Infraestrutura
```bash
# Clone o repositório
git clone ...

# Suba os containers (API + Redis + Postgres)
docker-compose up -d --build
```
A API estará disponível em `http://localhost:8000`.

## 🛡️ Filtro de Fidelidade (Pureza de Dados)
O motor utiliza o algoritmo **NeuralGate** para pontuar o conteúdo extraído. Somente dados com alta densidade de informação (Fidelidade > 0.6) são entregues, eliminando newsletters, headers, footers e anúncios.

---
**NeuralSafety Engineering** - *Data is the new fuel. We are the refinery.*
