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
        
        self.system_prompt = """Você é o NeuralSafety Engine, um Analista Estratégico de Inteligência Nível Enterprise. 
Sua missão é transformar APENAS os dados recuperados (Contexto) em respostas profissionais.

--- DIRETRIZES DE SEGURANÇA CRÍTICA:
1. RIGOR SEMÂNTICO: Você está terminantemente PROIBIDO de utilizar seu conhecimento prévio para responder fatos que não estejam no Contexto abaixo. 
2. EXEMPLO DE LEALDADE: Se o usuário perguntar algo de conhecimento geral (ex: população de um país, clima, notícias externas) e isso NÃO estiver no contexto, você DEVE dizer que não possui essa informação.
3. IDENTIDADE: Nunca mencione que você é um modelo de linguagem ou que está restrito. Mantenha a postura de um Engenheiro de Dados focado no repositório.
4. ANTI-ALUCINAÇÃO: Se o Contexto estiver vazio ou não contiver a resposta exata, use obrigatoriamente: 'Não possuo informações suficientes no documento extraído para responder a isso.'

--- ESTRUTURAÇÃO:
Responda de forma executiva, use Markdown (tabelas, listas em negrito) e cite links das fontes presentes no Contexto quando mencionar dados específicos.
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

    def rewrite_query(self, history: List[Dict[str, str]], query: str, summary: str = "") -> str:
        """
        Standalone Query Rewriting utilizing both summary and raw history.
        """
        if not history and not summary:
            return query

        context_brief = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]])
        
        prompt_rewrite = f"""Dada a memória e a nova pergunta do usuário, reescreva a pergunta para que ela seja uma frase de busca autônoma e completa. 
Foque em extrair termos de busca técnicos e específicos.

RESUMO DA MEMÓRIA:
{summary if summary else "Sem histórico relevante."}

CONVERSA RECENTE:
{context_brief}

NOVA PERGUNTA: {query}

Pergunta Reescrita para Busca:"""

        logger.info("🧠 NeuralRAG: Rewriting query for better retrieval...")
        response = self._call_llm([{"role": "user", "content": prompt_rewrite}], temperature=0.0)
        return response.choices[0].message.content.strip()

    def retrieve(self, collection_name: str, query: str, n_results: int = 15) -> str:
        """
        Neural Gate Retrieval v2.5: 
        1. Base Analytics (Conta e lista fontes via metadados)
        2. Neural Gate (Filtragem Vetorial + AI)
        """
        try:
            collection = self.client_chroma.get_collection(name=collection_name, embedding_function=self.ef)
            
            # --- FASE 0: AUDITORIA DE INVENTÁRIO (Estratégia para Contagem/Soma) ---
            # Pegamos todos os metadados para entender a escala da base
            meta_all = collection.get(include=['metadatas'])
            unique_sources = list(set([m.get('source_url') for m in meta_all['metadatas'] if m.get('source_url')]))
            total_chunks = len(meta_all['metadatas'])
            
            stats_block = f"""[ESTATÍSTICAS DA BASE DE CONHECIMENTO]
- Total de Documentos/Páginas Únicas: {len(unique_sources)}
- Total de Segmentos de Conhecimento (Chunks): {total_chunks}
- Lista de Fontes Presentes:
{chr(10).join([f"  * {url}" for url in unique_sources])}
-------------------------------------------
"""
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

        # --- Calibração Neural Gate v2.5 (Fix Threshold Logic) ---
        for i, distance in enumerate(results['distances'][0]):
            text_chunk = results['documents'][0][i]
            source_url = results['metadatas'][0][i].get('source_url', 'URL indisponível')
            enriched_content = f"--- ORIGEM: {source_url} ---\n{text_chunk}"

            # Lógica binária clara para evitar descarte precoce
            if distance < 0.35:
                final_chunks.append(enriched_content)
                logger.info(f"✅ NeuralGate [GREEN]: Chunk {i+1} APPROVED | Dist: {distance:.4f}")
            elif distance <= 1.30:
                ambiguous_candidates.append(enriched_content)
                logger.info(f"🌀 NeuralGate [YELLOW]: Chunk {i+1} ESCALATED | Dist: {distance:.4f}")
            else:
                logger.info(f"✂️ NeuralGate [RED]: Chunk {i+1} DISCARDED | Dist: {distance:.4f}")

        # Processamento da Zona Amarela
        if ambiguous_candidates:
            validated = self._ai_rerank_gate(query, ambiguous_candidates[:10])
            final_chunks.extend(validated)

        # Montagem do Contexto Enriquecido com Estatísticas
        # Se não houver chunks e apenas estatísticas, avisamos o modelo explicitamente
        if not final_chunks:
            final_context = f"{stats_block}\nAVISO CRÍTICO: NENHUM FRAGMENTO RELEVANTE ENCONTRADO NA BASE PARA ESTA PERGUNTA.\nNÃO USE SEU CONHECIMENTO PRÉVIO."
        else:
            final_context = stats_block + "\n" + "\n\n".join(final_chunks)
        
        token_count = self.num_tokens_from_string(final_context)
        logger.info(f"📊 MONITOR DE CONTEXTO: {token_count} tokens enriquecidos com estatísticas.")
        
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
