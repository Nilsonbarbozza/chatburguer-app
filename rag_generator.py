import os
import sys
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from core.rag_service import NeuralRAG
from core.memory_manager import SlidingWindowMemory
from core.ingestor import IngestorAgent
from core.pipeline import build_pipeline

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NeuralSafety")

# Load ENV
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or api_key == "sk-sua-chave-aqui":
    logger.error("🚨 CRITICAL: OPENAI_API_KEY nao configurada no arquivo .env ou ambiente.")
    # No Docker, preferimos deixar o container falhar para que o orquestrador (K8s/Compose) saiba do erro.
    raise RuntimeError("API Key ausente.")

# Initialize FastAPI
app = FastAPI(
    title="NeuralSafety Enterprise RAG API",
    version="1.0.0",
    docs_url="/api/docs", # Endpoint profissional de documentação
    redoc_url="/api/redoc"
)

# Habilita CORS para o navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services (Standardized for /app context)
rag_service = NeuralRAG(api_key=api_key)
memory_manager = SlidingWindowMemory(client_llm=rag_service.client_llm)
ingestor = IngestorAgent(openai_api_key=api_key)

# Servir arquivos estáticos (Frontend)
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Models
class ChatRequest(BaseModel):
    session_id: str
    message: str
    collection: str  # e.g., 'market_ebay_strict2'

class IngestRequest(BaseModel):
    url: str
    collection_name: Optional[str] = None # Se nulo, gera automatico
    strict: bool = True

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tokens_used: int
    collection: str
    economy: Optional[dict] = None

class IngestResponse(BaseModel):
    task_id: str
    status: str
    message: str
    collection: str

# ---------------------------------------------------------
# FUNCÕES DE FUNDO (BACKGROUND TASKS)
# ---------------------------------------------------------
def run_neural_sync(url: str, collection: str, strict: bool):
    """
    Background worker for Scrape -> Clean -> Ingest.
    """
    try:
        logging.info(f"🌀 NeuralSync Ativado: {url} -> {collection}")
        
        # 1. Pipeline Dataset (Modo Fantasma/Headless)
        # O ScraperStage já lê do contexto se deve ser headless? 
        # Na verdade, precisamos garantir que ScraperStage não abra janelas.
        # Por padrão ele está headless=False no scraper.py, vamos precisar ajustar.
        
        pipeline = build_pipeline(mode="dataset", strict=strict)
        
        # Executa Scrape & Processing
        result = pipeline.execute({
            "url": url,
            "mode": "dataset"
        })
        
        # 2. Ingestão dos vetores
        readable_path = result.get("dataset_readable_path")
        if not readable_path:
            # Fallback para o caminho padrão se o OutputStage não retornou
            readable_path = os.path.join("output", "dataset_readable.json")
            
        ingestor.ingest_dataset_file(readable_path, collection)
        logging.info(f"✅ NeuralSync Completo para {url}")
        
    except Exception as e:
        logging.error(f"❌ NeuralSync FALHOU para {url}: {e}")

import time

@app.get("/")
async def get_ui():
    """Serves the premium RAG interface."""
    return FileResponse("static/index.html")

@app.get("/collections")
async def list_collections_endpoint():
    """
    Returns all available collections in ChromaDB.
    """
    try:
        cols = ingestor.list_collections()
        return {"collections": cols}
    except Exception as e:
        logger.error(f"Erro ao listar colecoes: {e}")
        return {"collections": []}

@app.post("/ingest/url", response_model=IngestResponse)
async def ingest_url_endpoint(request: IngestRequest, bg_tasks: BackgroundTasks):
    """
    Triggers dynamic Scrape & Ingest pipeline.
    """
    # 1. Padroniza nome da coleção e limpa caracteres inválidos (acentos, espaços, etc)
    if request.collection_name:
        collection = ingestor.sanitize_name(request.collection_name)
    else:
        collection = ingestor.format_collection_name(request.url)
    
    # 2. Agenda a tarefa pesada para rodar em background
    bg_tasks.add_task(run_neural_sync, request.url, collection, request.strict)
    
    return IngestResponse(
        task_id=f"sync_{int(time.time())}",
        status="processing",
        message="NeuralSync iniciado com sucesso. O cérebro será atualizado em breve.",
        collection=collection
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Enterprise Chat Endpoint.
    Handles memory, query rewriting, retrieval and resilient generation.
    """
    try:
        # 1. Query Rewriting (using history)
        history = memory_manager.get_history_for_rewriting(request.session_id)
        optimized_query = rag_service.rewrite_query(history, request.message)
        
        # 2. Retrieval with Context Grounding
        context = rag_service.retrieve(request.collection, optimized_query)
        
        # 3. Memory Assembly (System Prompt + Summary + History + Context)
        messages, economy_metrics = memory_manager.get_messages(
            session_id=request.session_id,
            system_prompt=rag_service.system_prompt,
            context_rag=context,
            current_query=request.message
        )
        
        # 4. Generation
        result = rag_service.generate_response(messages)
        
        # 5. Persist Interaction
        memory_manager.add_interaction(request.session_id, request.message, result["content"])
        
        return ChatResponse(
            session_id=request.session_id,
            response=result["content"],
            tokens_used=result["usage"].total_tokens,
            collection=request.collection,
            economy=economy_metrics
        )

    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Provides a fallback for local terminal execution if needed, 
    # but primarily run via: uvicorn rag_generator:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
