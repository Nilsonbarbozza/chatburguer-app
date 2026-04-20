import os
import logging
from typing import List, Dict, Any, Optional
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
    def __init__(self, api_key: str, chroma_path: str = "./vector_db"):
        self.api_key = api_key
        self.client_llm = OpenAI(api_key=api_key)
        self.client_chroma = chromadb.PersistentClient(path=chroma_path)
        
        # Unified Embedding Engine (Enterprise Standard)
        self.ef = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
        
        self.system_prompt = """Você é um assistente corporativo de elite.
A sua função é responder à pergunta do usuário baseando-se ÚNICA E EXCLUSIVAMENTE no Contexto fornecido.

Regras Estritas:
1. Se a resposta não estiver contida no contexto, diga exatamente: 'Não possuo informações suficientes no documento para responder a isso.'
2. Não utilize conhecimentos prévios externos.
3. Prioridade de Links: Sempre que houver links de produtos específicos (que contêm '/itm/'), use-os em preferência a links de busca genérica.
4. Citação: Sempre forneça o link direto para o produto mencionado para facilitar a compra do usuário.
5. Seja direto, claro e profissional.
"""

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

    def retrieve(self, collection_name: str, query: str, n_results: int = 3, threshold: float = 1.30) -> str:
        """
        Retrieves grounded context from ChromaDB with dynamic cost pruning.
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

        filtered_chunks = []
        for i, distance in enumerate(results['distances'][0]):
            if distance < threshold:
                text_chunk = results['documents'][0][i]
                source_url = results['metadatas'][0][i].get('source_url', 'URL indisponível')
                
                # Context Enrichment
                enriched_chunk = f"--- ORIGEM: {source_url} ---\n{text_chunk}"
                filtered_chunks.append(enriched_chunk)
                logger.info(f"✅ Chunk {i+1} approved | Distance: {distance:.4f}")
            else:
                logger.info(f"✂️ Chunk {i+1} discarded | Distance: {distance:.4f}")

        if not filtered_chunks:
            return "Nenhum contexto relevante encontrado no documento."
        
        return "\n\n".join(filtered_chunks)

    def generate_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Final generation step using the enriched message stack.
        """
        logger.info("🚀 NeuralRAG: Generating final response...")
        response = self._call_llm(messages)
        
        return {
            "content": response.choices[0].message.content,
            "usage": response.usage
        }
