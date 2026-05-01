import os
import logging
from typing import List, Dict, Any, Optional
import tiktoken
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NeuralRAG")

class NeuralRAG:
    """
    Enterprise-grade RAG core service.
    Handles resilient AI interactions, vector search, and context grounding.
    """
    def __init__(self, api_key: str, chroma_path: str = None):
        self._api_key = api_key
        self.client_llm = OpenAI(api_key=self._api_key)
        
        # Puxa o caminho do banco da variável de ambiente (Caminho ABSOLUTO)
        raw_path = chroma_path or os.getenv("CHROMA_DB_PATH", "data/vector_db")
        self.vector_db_path = os.path.abspath(raw_path)
        self.client_chroma = chromadb.PersistentClient(path=self.vector_db_path)
        
        # Unified Embedding Engine (Enterprise Standard)
        # Otimizado com 512 dimensões (Matryoshka) para escala e precisão
        self.ef = OpenAIEmbeddingFunction(
            api_key=self._api_key,
            model_name="text-embedding-3-small",
            dimensions=512
        )
        
        # Tokenizador para auditoria de custos (cl100k_base para modelos v3)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self.system_prompt = """Você atua como um Engenheiro de Dados Sênior de Elite.
A sua função é analisar os dados recuperados, extrair insights e substituir o pensamento humano na produtividade analítica, baseando-se ÚNICA E EXCLUSIVAMENTE no Contexto fornecido.

Sua arquitetura de resposta deve ser IRREPREENSÍVEL E RICA:
1. Formatação Avançada: Use estruturação inteligente em Markdown, criando tópicos (bullet points) claros e destacando métricas vitais ou palavras-chave em **negrito**.
2. Organização Visual: Construa tabelas em Markdown sempre que precisar apresentar dados comparativos, históricos ou quantitativos.
3. Citação de Fontes: Sempre que a extração possuir links originais ou de produtos (ex: contendo '/itm/' ou links de cotações), incorpore-os naturalmente no texto final para validação.
4. Anti-Alucinação Estrita: Sua inteligência analítica só se aplica ao que extraímos. Se a resposta da dúvida do usuário NÃO estiver contida nos documentos fornecidos, recuse-se a responder dizendo explicitamente: 'Não possuo informações suficientes no documento extraído para responder a isso.'
5. Mantenha o padrão corporativo analítico de um relatório de alto valor. Não seja monótono, demonstre cruzamento inteligente de dados.
"""

    def num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        return len(self.tokenizer.encode(string))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Any:
        """Resilient LLM call with exponential backoff."""
        return self.client_llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature
        )

    def rewrite_query(self, history: List[Dict[str, str]], query: str) -> str:
        """
        Standalone Query Rewriting to improve retrieval accuracy.
        Transforms fuzzy user queries into precise search terms.
        """
        if not history:
            return query

        context_brief = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]])
        
        prompt_rewrite = f"""Dada a conversa abaixo e a nova pergunta do usuário, reescreva a pergunta para que ela seja uma frase de busca autônoma e completa para um banco de dados. 
Inclua nomes de produtos, marcas ou especificações técnicas necessárias.
Não responda a pergunta, APENAS retorne a pergunta reescrita.

Conversa Recente:
{context_brief}

Nova Pergunta do Usuário: {query}

Pergunta Reescrita para Busca:"""

        logger.info("🧠 NeuralRAG: Rewriting query for better retrieval...")
        response = self._call_llm([{"role": "user", "content": prompt_rewrite}], temperature=0.0)
        return response.choices[0].message.content.strip()

    def retrieve(self, collection_name: str, query: str, n_results: int = 15) -> str:
        """
        Neural Gate Retrieval: 
        1. Hierarchical search (Matryoshka 512d)
        2. Tiered Filtering (Math + AI Reranking)
        """
        try:
            collection = self.client_chroma.get_collection(name=collection_name, embedding_function=self.ef)
        except Exception as e:
            logger.error(f"Collection '{collection_name}' not found: {e}")
            return "Erro: Base de conhecimento não disponível."

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )

        final_chunks = []
        ambiguous_candidates = []

        # --- Neural Gate Logic ---
        for i, distance in enumerate(results['distances'][0]):
            text_chunk = results['documents'][0][i]
            source_url = results['metadatas'][0][i].get('source_url', 'URL indisponível')
            enriched_content = f"--- ORIGEM: {source_url} ---\n{text_chunk}"

            if distance < 0.22:
                # ZONA VERDE: Confiança Matemática Total
                final_chunks.append(enriched_content)
                logger.info(f"✅ NeuralGate [GREEN]: Chunk {i+1} AUTO-APPROVED | Dist: {distance:.4f}")
            elif 0.22 <= distance <= 0.48:
                # ZONA AMARELA: Ambiguidade (Escala para Reranking)
                ambiguous_candidates.append(enriched_content)
                logger.info(f"🌀 NeuralGate [YELLOW]: Chunk {i+1} ESCALATED | Dist: {distance:.4f}")
            else:
                # ZONA VERMELHA: Ruído Semântico
                logger.info(f"✂️ NeuralGate [RED]: Chunk {i+1} DISCARDED | Dist: {distance:.4f}")

        # Processamento da Zona Amarela via Neural Gate (IA)
        if ambiguous_candidates:
            # Aumentamos para 10 para maior escala e precisão
            validated = self._ai_rerank_gate(query, ambiguous_candidates[:10])
            final_chunks.extend(validated)

        if not final_chunks:
            # Explicitamente informa que o contexto é vazio para evitar que o LLM use conhecimento interno
            return "Vazio: O documento não contém nenhuma informação sobre este assunto."
        
        final_context = "\n\n".join(final_chunks)
        
        # Auditoria de Tokens Real-time
        token_count = self.num_tokens_from_string(final_context)
        logger.info(f"📊 MONITOR DE CONTEXTO: {token_count} tokens serão enviados ao GPT.")
        
        return final_context

    def _ai_rerank_gate(self, query: str, candidates: List[str]) -> List[str]:
        """
        AI Bouncer: Re-ranqueamento binário ultra-rápido usando GPTo-mini.
        Filtra chunks que parecem relevantes (vetorialmente) mas não respondem à dúvida.
        """
        approved = []
        try:
            for i, chunk in enumerate(candidates):
                # Prompt mais sofisticado: foca em 'qualquer pista' para ser mais robusto
                prompt = (
                    f"CONTEXTO PARA ANALISAR:\n{chunk[:1500]}\n\n"
                    f"PERGUNTA DO USUÁRIO: {query}\n\n"
                    "INSTRUÇÃO: Este texto contém QUALQUER dado, número ou informação que ajude a responder a pergunta acima? "
                    "Responda apenas [SIM] se for útil ou [NAO] se for irrelevante."
                )
                
                response = self.client_llm.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=6,
                    temperature=0.0
                )
                
                result = response.choices[0].message.content.strip().upper()
                if "[SIM]" in result:
                    approved.append(chunk)
                    logger.info(f"💎 NeuralGate [AI]: Chunk {i+1} VALIDATED.")
                else:
                    logger.info(f"🗑️ NeuralGate [AI]: Chunk {i+1} REJECTED.")
            
            return approved
        except Exception as e:
            logger.error(f"Falha no processamento Neural Gate IA: {e}")
            return []

    def generate_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Agentic Generation: Decides if it needs more context via WebFetch API.
        """
        logger.info("🚀 NeuralRAG: Initiating Agentic Generation...")
        
        # Definição das ferramentas disponíveis para o Agente
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "neuralsafety_webfetch",
                    "description": "Extrai conteúdo de artigos, notícias e sites corporativos em Markdown limpo. Use SEMPRE que o usuário fornecer uma URL ou quando o contexto do RAG for insuficiente sobre um link específico.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "A URL completa do site alvo."},
                            "force_stealth": {"type": "boolean", "description": "Ative se o site tiver bloqueios fortes."}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neuralsafety_search_and_fetch",
                    "description": "Busca na internet por eventos recentes e extrai o conteúdo das duas melhores fontes. Use quando o usuário fizer perguntas sobre notícias, eventos atuais ou pedir pesquisas SEM fornecer um link.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": { "type": "string", "description": "A frase de busca otimizada (ex: 'novas regulamentações de IA na Europa 2026')." },
                            "force_stealth": { "type": "boolean" }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        # 1ª Tentativa: O modelo decide se responde ou usa ferramenta
        response = self.client_llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Se o Agente decidiu que precisa de reforço (WebFetch)
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                import json
                if tool_call.function.name == "neuralsafety_webfetch":
                    args = json.loads(tool_call.function.arguments)
                    url = args.get("url")
                    
                    # Chamada interna para a nossa API (Batalhão)
                    fetch_content = self._internal_webfetch(url, args.get("force_stealth", False))
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": fetch_content
                    })
                
                elif tool_call.function.name == "neuralsafety_search_and_fetch":
                    args = json.loads(tool_call.function.arguments)
                    query = args.get("query")
                    
                    # Chamada interna para a nossa API de Busca e Extração
                    fetch_content = self._internal_search_and_fetch(query, args.get("force_stealth", False))
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": fetch_content
                    })
            
            # 2ª Chamada: Agora com o conteúdo extraído injetado
            logger.info("🧠 NeuralRAG: Injetando extração em tempo real na resposta final...")
            response = self.client_llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

        return {
            "content": response.choices[0].message.content,
            "usage": response.usage
        }

    def _internal_webfetch(self, url: str, force_stealth: bool) -> str:
        """Helper para bater na API interna de WebFetch."""
        api_url = "http://localhost:8000/api/v1/fetch"
        api_key = "sk-neuralsafety-enterprise-v1"
        
        logger.info(f"⚡ [AGENTIC RAG] Buscando reforço externo direto: {url}")
        
        try:
            import requests
            headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
            payload = {"url": url, "force_stealth": force_stealth}
            
            res = requests.post(api_url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()
            return res.json().get("markdown_body", "Conteúdo vazio ou erro na extração.")
        except Exception as e:
            logger.error(f"Erro na integração Agentic: {e}")
            return f"Erro ao acessar fonte externa: {str(e)}"

    def _internal_search_and_fetch(self, query: str, force_stealth: bool) -> str:
        """Helper para bater na API interna de Busca e Extração."""
        api_url = "http://localhost:8000/api/v1/search_and_fetch"
        api_key = "sk-neuralsafety-enterprise-v1"
        
        logger.info(f"📡 [AGENTIC RAG] Acionando Radar para: '{query}'")
        
        try:
            import requests
            headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
            payload = {"query": query, "force_stealth": force_stealth}
            
            res = requests.post(api_url, json=payload, headers=headers, timeout=45)
            res.raise_for_status()
            data = res.json()
            urls = data.get("urls_processed", [])
            logger.info(f"✅ Radar concluiu em {data.get('processing_ms')}ms. URLs processadas: {urls}")
            return data.get("consolidated_markdown", "Nenhum conteúdo pôde ser extraído da busca.")
        except Exception as e:
            logger.error(f"Erro no Radar Agentic: {e}")
            return f"Erro ao realizar busca e extração: {str(e)}"
