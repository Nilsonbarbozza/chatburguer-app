import os
import json
import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import Dict, Any, List

logger = logging.getLogger('neural_ingestor')

class IngestorAgent:
    def __init__(self, vector_db_path: str = None, openai_api_key: str = None):
        raw_path = vector_db_path or os.getenv("CHROMA_DB_PATH", "data/vector_db")
        self.vector_db_path = os.path.abspath(raw_path)
        self._api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY não encontrada para o IngestorAgent.")

        # Initialize Chroma Client
        self.client = chromadb.PersistentClient(path=self.vector_db_path)
        
        # Enterprise Embedding Engine
        self.ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self._api_key,
            model_name="text-embedding-3-small",
            dimensions=512
        )

    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Garante que o nome da coleção seja compatível com o ChromaDB:
        - Apenas [a-zA-Z0-9._-]
        - Começa e termina com alfanumérico
        - Sem acentos
        """
        import unicodedata
        import re
        
        # Remove acentos
        nfkd_form = unicodedata.normalize('NFKD', name)
        name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        
        # Converte para minúsculo e substitui espaços/ífens por _
        name = name.lower().replace(" ", "_").replace("-", "_")
        
        # Remove caracteres não permitidos
        name = re.sub(r'[^a-zA-Z0-9._-]', '', name)
        
        # Garante que começa e termina com alfanumérico
        name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
        name = re.sub(r'[^a-zA-Z0-9]+$', '', name)
        
        return name

    @staticmethod
    def format_collection_name(url: str) -> str:
        """
        Converts a URL domain to a safe ChromaDB collection name.
        Example: https://pt.tradingeconomics.com -> sync_tradingeconomics
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if not domain:
            return "sync_unknown"
        
        parts = domain.split('.')
        # Ignora prefixos comuns (www, pt, en, br, etc)
        ignored_prefixes = ['www', 'pt', 'en', 'br', 'es', 'it']
        
        if parts[0] in ignored_prefixes and len(parts) > 1:
            base_name = parts[1]
        else:
            base_name = parts[0]
        
        # Usa o novo sanitizador
        clean_name = IngestorAgent.sanitize_name(base_name)
        return f"sync_{clean_name}"

    def list_collections(self) -> List[str]:
        """Returns a list of all existing collection names."""
        return [c.name for c in self.client.list_collections()]

    def ingest_dataset_file(self, file_path: str, collection_name: str) -> Dict[str, Any]:
        """
        Loads a readable dataset JSON and syncs it with ChromaDB.
        """
        logger.info(f"🚀 Iniciando sincronização: {file_path} -> Collection: {collection_name}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo de dataset não encontrado: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract chunks from the pipeline output
            # O build_pipeline do cloner no modo 'dataset' gera uma lista de páginas
            # Cada página tem 'content' -> 'semantic_chunks'
            # Extract chunks from the pipeline output
            # Suporta ambos os schemas: o antigo (metadata/content) e o v2_batalhao (url/data)
            all_chunks = []
            for page in data:
                # 1. Tenta extrair a URL (Fonte)
                url = page.get("url") or page.get("metadata", {}).get("source_url", "unknown_source")
                
                # 2. Tenta extrair os chunks semânticos
                # No v2_batalhao fica em page['data']['semantic_chunks']
                # No antigo ficava em page['content']['semantic_chunks']
                content_obj = page.get("data") or page.get("content", {})
                chunks = content_obj.get("semantic_chunks", [])
                
                for chunk in chunks:
                    chunk_text = chunk.get("text")
                    if chunk_text:
                        all_chunks.append({
                            "content": chunk_text,
                            "metadata": {"source_url": url}
                        })

            if not all_chunks:
                logger.warning(f"⚠️ Nenhum texto válido encontrado para ingestão em {file_path}")
                return {"status": "warning", "message": "Nenhum texto válido encontrado no arquivo."}

            # Create/Load Collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.ef
            )

            # Ingest in batch
            documents = [c["content"] for c in all_chunks]
            metadatas = [c["metadata"] for c in all_chunks]
            ids = [f"id_{collection_name}_{i}" for i in range(len(all_chunks))]

            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"✅ Sincronização concluída: {len(documents)} vetores injetados.")
            return {
                "status": "success",
                "collection": collection_name,
                "chunks_count": len(documents)
            }
        except Exception as e:
            logger.error(f"❌ Falha na ingestão: {e}")
            raise

    def ingest_jsonl_file(self, file_path: str, collection_name: str) -> Dict[str, Any]:
        """
        Loads a JSONL dataset (one JSON per line) and syncs it with ChromaDB.
        Ex: ds_academy_articles_phase2_2026-04-27.jsonl
        """
        logger.info(f"🚀 Iniciando Ingestão JSONL: {file_path} -> Collection: {collection_name}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo JSONL não encontrado: {file_path}")

        try:
            all_chunks = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    page = json.loads(line)
                    url = page.get("url") or "unknown_source"
                    content_obj = page.get("data") or {}
                    chunks = content_obj.get("semantic_chunks", [])
                    
                    for chunk in chunks:
                        chunk_text = chunk.get("text")
                        if chunk_text:
                            # Preservamos metadados vitais para o RAG
                            all_chunks.append({
                                "content": chunk_text,
                                "metadata": {
                                    "source_url": url,
                                    "title": content_obj.get("title", "Sem Título")
                                }
                            })

            if not all_chunks:
                logger.warning(f"⚠️ Nenhum chunk encontrado no arquivo JSONL: {file_path}")
                return {"status": "warning", "message": "Nenhum dado encontrado."}

            # Create/Load Collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.ef
            )

            # Ingestão em Lotes (Batches) para evitar estouro de memória
            batch_size = 100
            total_ingested = 0
            
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                
                documents = [c["content"] for c in batch]
                metadatas = [c["metadata"] for c in batch]
                ids = [f"id_{collection_name}_{total_ingested + j}" for j in range(len(batch))]
                
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                total_ingested += len(batch)
                logger.info(f"📥 Progresso: {total_ingested}/{len(all_chunks)} chunks injetados...")

            logger.info(f"✅ Ingestão JSONL concluída com sucesso: {total_ingested} vetores.")
            return {
                "status": "success",
                "collection": collection_name,
                "chunks_count": total_ingested
            }

        except Exception as e:
            logger.error(f"❌ Falha catastrófica na ingestão JSONL: {e}")
            raise
