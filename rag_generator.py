import os
import sys
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from core.rag_service import NeuralRAG
from core.memory_manager import SlidingWindowMemory

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Load ENV
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or api_key == "sk-sua-chave-aqui":
    print("Erro: OPENAI_API_KEY nao configurada no arquivo .env")
    sys.exit(1)

# Initialize FastAPI
app = FastAPI(title="NeuralSafety Enterprise RAG API", version="1.0.0")

# Habilita CORS para o navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Cores
rag_service = NeuralRAG(api_key=api_key)
memory_manager = SlidingWindowMemory(client_llm=rag_service.client_llm)

# Servir arquivos estáticos (Frontend)
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Models
class ChatRequest(BaseModel):
    session_id: str
    message: str
    collection: str  # e.g., 'market_ebay_strict2'

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tokens_used: int
    collection: str

@app.get("/")
async def get_ui():
    """Serves the premium RAG interface."""
    return FileResponse("static/index.html")

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
        messages = memory_manager.get_messages(
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
            collection=request.collection
        )

    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Provides a fallback for local terminal execution if needed, 
    # but primarily run via: uvicorn rag_generator:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
