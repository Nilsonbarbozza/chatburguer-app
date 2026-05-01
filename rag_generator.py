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
    raise RuntimeError("API Key ausente.")

# Initialize FastAPI
app = FastAPI(
    title="NeuralSafety Enterprise RAG API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Habilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
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
    collection: str

class IngestRequest(BaseModel):
    url: str
    collection_name: Optional[str] = None
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
async def run_neural_sync(url: str, collection: str, strict: bool):
    """
    Background worker for Scrape -> Clean -> Ingest via Agentic WebFetch API.
    """
    try:
        logging.info(f"🌀 NeuralSync Ativado via API: {url} -> {collection}")
        
        # Placeholder para chamada da Agentic API (WebFetchAPI branch)
        # Em breve: response = await call_agentic_webfetch(url, force_stealth=strict)
        # ingest_result = await ingestor.ingest_direct(response.chunks, collection)
        
        logging.info(f"✅ NeuralSync (Stub) completado para {url}.")
        
    except Exception as e:
        logging.error(f"❌ NeuralSync FALHOU para {url}: {e}")
        raise 

@app.get("/")
async def get_ui():
    """Serves the premium RAG interface."""
    return FileResponse("static/index.html")

@app.get("/collections")
async def list_collections_endpoint():
    """Returns all available collections in ChromaDB."""
    try:
        cols = ingestor.list_collections()
        return {"collections": cols}
    except Exception as e:
        logger.error(f"Erro ao listar colecoes: {e}")
        return {"collections": []}

@app.post("/ingest/url", response_model=IngestResponse)
async def ingest_url_endpoint(request: IngestRequest):
    """Triggers dynamic Scrape & Ingest pipeline."""
    # Padroniza nome da coleção
    if request.collection_name:
        collection = ingestor.sanitize_name(request.collection_name)
    else:
        collection = ingestor.format_collection_name(request.url)
    
    try:
        # Nota: Agora run_neural_sync é async, então chamamos diretamente ou via BackgroundTasks
        await run_neural_sync(request.url, collection, request.strict)
        
        return IngestResponse(
            task_id=f"sync_{int(time.time())}",
            status="success",
            message="NeuralSync concluído (Stub)! A base de conhecimento será alimentada via API.",
            collection=collection
        )
    except Exception as e:
        logger.error(f"Ingest endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Enterprise Chat Endpoint."""
    try:
        # 1. Query Rewriting
        history = memory_manager.get_history_for_rewriting(request.session_id)
        optimized_query = rag_service.rewrite_query(history, request.message)
        
        # 2. Retrieval
        context = rag_service.retrieve(request.collection, optimized_query)
        
        # 3. Memory Assembly
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
