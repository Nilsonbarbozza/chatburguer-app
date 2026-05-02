Comandante, a **Operação Radar** acaba de receber luz verde.

A sua decisão de reduzir a busca para apenas **2 links quentes** usando a **Tavily API** é um movimento tático brilhante. Dois links são suficientes para fornecer o contexto de "hoje" (cruzamento de fontes) sem estourar o limite de tokens da janela de contexto do LLM do cliente e garantindo uma velocidade de resposta fulminante. É esse tipo de eficiência de recursos que as pequenas e médias empresas europeias que visitaremos valorizam na hora de assinar contratos de tecnologia.

Aqui está a **OS-002** pronta para você disparar para o Esquadrão de Código.

---

### 📜 ORDEM DE SERVIÇO: OS-002 (Operação Radar - Tiro Único)

**De:** Arquiteto-Chefe / Comando Geral
**Para:** Esquadrão de Código & Area 51
**Missão:** Implementar o Endpoint `/search_and_fetch` acoplado ao buscador Tavily.

#### 🎯 O Briefing Estratégico

O Batalhão agora terá um "Radar". Vamos plugar a API da Tavily (um buscador construído especificamente para IAs) na nossa esteira. O fluxo deve ser: o cliente envia uma query em texto livre -> Nós batemos na Tavily (buscando os 2 links mais relevantes) -> Invadimos os 2 links simultaneamente -> Limpamos ambos na memória RAM -> Devolvemos um documento único consolidado em menos de 2 segundos.

#### 🛠️ Fase 1: Atualização dos Contratos (Pydantic)

No arquivo `agentic_api/schemas.py`, criem o molde para o novo endpoint:

```python
class SearchFetchRequest(BaseModel):
    query: str
    force_stealth: bool = False
    fidelity_threshold: float = 0.6

class SearchFetchResponse(BaseModel):
    query: str
    urls_processed: list[str]
    processing_ms: int
    consolidated_markdown: str
```

#### 📡 Fase 2: O Radar (Integração Tavily)

Para não travar nosso _Event Loop_, não usem bibliotecas síncronas. Usem o `aiohttp` (que já temos) para fazer um POST assíncrono para a API da Tavily.

- **Endpoint Alvo:** `https://api.tavily.com/search`
- **Payload Obrigatório:** `{"api_key": "SUA_CHAVE", "query": request.query, "search_depth": "basic", "include_answer": False, "max_results": 2}`
- Essa chamada deve levar cerca de 200ms.

#### ⚡ Fase 3: O Ataque Simultâneo (O Coração da Missão)

No arquivo `agentic_api/routes.py`, criem a rota `POST /v1/agent/search_and_fetch`. A mágica do paralelismo acontece aqui:

1. Após receber as 2 URLs da Tavily, não façam um loop `for` comum (isso dobraria o tempo).
2. Usem **`asyncio.gather()`** para disparar o Batalhão (L0 ou L12) contra as 2 URLs exata e simultaneamente.
3. Quando o HTML dos 2 sites voltar, enviem a lista para o `ProcessPoolExecutor` rodar o _DataClear_.
4. O resultado final deve concatenar o Markdown dos 2 sites com divisórias claras.

**Exemplo de Concatenação no Código:**

```python
consolidated_markdown = f"# Fonte 1: {title_1}\n{markdown_1}\n\n---\n\n# Fonte 2: {title_2}\n{markdown_2}"
```

#### 🧩 Fase 4: O Novo Snippet do Cliente

Adicionem este novo _Tool Schema_ na documentação oficial para que o cliente saiba como invocar o Tiro Único:

```json
{
  "type": "function",
  "function": {
    "name": "neuralsafety_search_and_fetch",
    "description": "Busca na internet por eventos recentes e extrai o conteúdo completo das duas melhores fontes. Use quando o usuário fizer perguntas abertas sobre notícias ou dados atuais sem fornecer um link.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "A frase de busca otimizada."
        }
      },
      "required": ["query"]
    }
  }
}
```

---

### 🎯 Definition of Done (Critérios de Aceite)

A missão será considerada concluída quando o terminal passar nestes 3 testes:

1. **O Teste da Latência:** Enviar um POST com a query `"Últimas notícias mercado IA"` e receber o Markdown consolidado dos 2 sites em **menos de 2.5 segundos** totais.
2. **O Teste da Resiliência:** Se a Tavily retornar apenas 1 link válido, o Batalhão deve processar esse 1 link sem quebrar a execução (`asyncio.gather` deve lidar com listas dinâmicas).
3. **O Teste de Queda do Alvo:** Se um dos 2 sites der Timeout (HTTP 504), a nossa API deve retornar o Markdown do site que sobreviveu, adicionando um aviso breve sobre a falha da segunda fonte, sem derrubar a requisição principal.

---

Pode disparar essa ordem, Comandante. Assim que o Esquadrão de Código acoplar a chave da Tavily e o `asyncio.gather` entrar em ação, nós teremos um motor duplo imparável. Aguardo o relatório de execução!
