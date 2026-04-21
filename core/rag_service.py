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
    def __init__(self, api_key: str, chroma_path: str = "./vector_db"):
        self.api_key = api_key
        self.client_llm = OpenAI(api_key=api_key)
        self.client_chroma = chromadb.PersistentClient(path=chroma_path)
        
        # Unified Embedding Engine (Enterprise Standard)
        # Otimizado com 512 dimensões (Matryoshka) para escala e precisão
        self.ef = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small",
            dimensions=512
        )
        
        # Tokenizador para auditoria de custos (cl100k_base para modelos v3)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self.system_prompt = """Você é um assistente corporativo de elite.
A sua função é responder à pergunta do usuário baseando-se ÚNICA E EXCLUSIVAMENTE no Contexto fornecido.

Regras Estritas:
1. Se a resposta não estiver contida no contexto, diga exatamente: 'Não possuo informações suficientes no documento para responder a isso.'
2. Não utilize conhecimentos prévios externos.
3. Prioridade de Links: Sempre que houver links de produtos específicos (que contêm '/itm/'), use-os em preferência a links de busca genérica.
4. Citação: Sempre forneça o link direto para o produto mencionado para facilitar a compra do usuário.
5. Seja direto, claro e profissional.
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
        Final generation step using the enriched message stack.
        """
        logger.info("🚀 NeuralRAG: Generating final response...")
        response = self._call_llm(messages)
        
        return {
            "content": response.choices[0].message.content,
            "usage": response.usage
        }

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
