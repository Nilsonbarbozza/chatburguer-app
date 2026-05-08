from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

from agentic_api.routes import router
from core.database import db

app = FastAPI(
    title="NeuralSafety Agentic WebFetch API",
    description="High-performance synchronous extraction and purification engine for Autonomous AI Agents.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
def health_check():
    return {"status": "online", "message": "NeuralSafety Agentic API is running"}
   

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.close()

# Conectando as rotas de extração ao aplicativo principal
app.include_router(router, prefix="/api/v1")

@app.get("/health", tags=["Infraestrutura"])
async def health_check():
    """
    Teste de Pulso (Healthcheck).
    Verifica se o container está de pé e respondendo rapidamente.
    """
    return {
        "status": "operational", 
        "system": "NeuralSafety Agentic API",
        "version": "1.0.0"
    }

@app.get("/metrics", tags=["Infraestrutura"])
async def metrics():
    """
    Estatísticas globais de consumo (Stub).
    Em produção, conectaremos ao Redis para puxar o consumo de APIs Key.
    """
    return {
        "status": "operational", 
        "note": "A auditoria detalhada de consumo estará ativa na v1.1"
    }
