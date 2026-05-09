from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

class FetchRequest(BaseModel):
    """
    Contrato de Entrada para a NeuralSafety Agentic API.
    Define as regras de engajamento para a extração do conteúdo.
    """
    url: HttpUrl = Field(
        ..., 
        description="URL alvo para extração. Deve ser uma URL HTTP/HTTPS válida."
    )
    
    force_stealth: bool = Field(
        default=False,
        description="Se True, aciona a evasão L12 (TLS Spoofing via curl_cffi). Mais lento, porém fura a maioria dos WAFs."
    )
    
    render_js: bool = Field(
        default=False,
        description="Deep Stealth Mode. Se True, aciona L34 (Playwright) para renderizar JavaScript pesado. Aumenta o timeout para 45s."
    )
    
    fidelity_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Limiar de fidelidade para descarte de lixo (0.0 a 1.0). Textos abaixo do limiar não geram semantic chunks."
    )
    
    archetype: str = Field(
        default="blog",
        description="Arquétipo de estruturação esperado (ex: blog, doc, ecommerce)."
    )

class FetchResponse(BaseModel):
    """
    Contrato de Saída da NeuralSafety Agentic API.
    A entrega do artefato limpo e estruturado.
    """
    status: str = Field(..., description="Status da extração (success, error, blocked).")
    url: str = Field(..., description="A URL processada.")
    markdown_body: str = Field(..., description="Conteúdo purificado e estruturado em Markdown.")
    semantic_chunks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Fragmentos semânticos destilados, prontos para vetorização (RAG)."
    )
    processing_ms: int = Field(..., description="Tempo total de processamento em milissegundos.")
    executor_used: str = Field(..., description="O arsenal utilizado na extração (L0-aiohttp, L12-curlcffi, L34-playwright).")
    error_message: Optional[str] = Field(None, description="Detalhes do erro, caso o status não seja success.")

class SearchFetchRequest(BaseModel):
    """
    Contrato de Entrada para a busca radar combinada com extração.
    """
    query: str = Field(..., description="A frase de busca otimizada para o radar (Tavily).")
    force_stealth: bool = Field(default=False, description="Ativa evasão pesada nas URLs descobertas.")
    fidelity_threshold: float = Field(default=0.6, description="Limiar de fidelidade para o DataClear.")

class SearchResultItem(BaseModel):
    url: str = Field(..., description="A URL de origem do conteúdo.")
    markdown_body: str = Field(..., description="Conteúdo purificado e estruturado em Markdown.")
    semantic_chunks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Fragmentos semânticos destilados com seus metadados preservados."
    )

class SearchFetchResponse(BaseModel):
    """
    Contrato de Saída para o tiro duplo consolidado.
    """
    query: str = Field(..., description="A query que originou a busca.")
    urls_processed: List[str] = Field(..., description="As URLs que foram extraídas com sucesso.")
    processing_ms: int = Field(..., description="Tempo total desde a busca até a limpeza final.")
    results: List[SearchResultItem] = Field(..., description="Resultados detalhados com markdown e chunks semânticos por URL.")
    error_message: Optional[str] = Field(None, description="Avisos sobre fontes que falharam ou erros gerais.")
