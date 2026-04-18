"""
core/stages/dataclear.py
Stage especializado para destilação de dados e conformidade para LLMs/RAG.
"""
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any
from core.pipeline import ProcessorStage
from core.utils import setup_logging

try:
    from markdownify import markdownify as md_converter
except ImportError:
    md_converter = None

setup_logging()
logger = logging.getLogger('html_processor')

class DataClearStage(ProcessorStage):
    """
    Agente de limpeza e estruturação de dados (AgenteDataClear).
    Transforma o soup em um dataset JSONL otimizado.
    """
    def __init__(self, redact_pii: bool = True):
        self.redact = redact_pii
        # Tags de ruído que não agregam conhecimento útil para LLM
        # Removido 'aside' e 'form' para não quebrar Buy Boxes e seletores de variante
        self.noise_tags = [
            'script', 'style', 'nav', 'footer', 'header', 
            'iframe', 'noscript', 'svg', 
            'canvas', 'video', 'audio'
        ]

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"=== AgenteDataClear: Iniciando Refino Semântico (Redigir PII: {self.redact}) ===")
        
        soup = context.get('soup')
        if not soup:
            logger.error("Soup não encontrado no contexto. Pulando DataClearStage.")
            return context

        # 1. Destilação (The Distiller)
        # Trabalhamos em uma cópia para não corromper o HTML original se for necessário depois
        from bs4 import BeautifulSoup
        clean_soup = BeautifulSoup(str(soup), 'lxml')
        
        # Remove tags de ruído
        for tag in clean_soup(self.noise_tags):
            tag.decompose()
            
        # Limpeza de classes de ruído comuns (Regex mais restrita com delimitações de limite de palavra)
        # Evitando o uso de 'ad-' solto que pode coincidir com 's-item__ad' (itens patrocinados úteis)
        noise_classes = re.compile(r'\b(cookie-notice|cookie-banner|social-share|popup-overlay|modal-overlay)\b', re.I)
        for tag in clean_soup.find_all(class_=noise_classes):
            tag.decompose()

        # 2. Conversão para Markdown (The MD-Transformer)
        if md_converter:
            markdown_body = md_converter(
                str(clean_soup), 
                heading_style="ATX", 
                bullets="-",
                # Mantemos as tags <a> e <img> para que o Markdownify converta em `[texto](url)` 
                # e `![alt](img)` preservando a semântica visual e links confome o docs/ defende.
            )
        else:
            logger.warning("markdownify não disponível. Usando fallback de texto simples.")
            markdown_body = clean_soup.get_text(separator='\n\n')

        # 2.5 Normalização Anti-Ruído e Caracteres Especiais Avançada
        # Remove caracteres invisíveis e 'Invisible Separators' sem destruir o Markdown
        import unicodedata
        markdown_body = unicodedata.normalize("NFKC", markdown_body)
        # O espectro de U+2060 a U+206F inclui o \u2063 (Invisible Separator) usado pelo eBay
        markdown_body = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u206f\xad\ufeff]', '', markdown_body)
        markdown_body = re.sub(r'[ \t]+', ' ', markdown_body) # Remove excesso de espaços no meio das palavras
        
        # Anti-Ofuscação CSS (O "Sniper" de Letras Soltas):
        # Muitas vezes o rastreio anti-bot quebra a palavra em múltiplas linhas e até usa alfabetos
        # cirílicos (como 'Р' ou 'о') para bypassar regex básicos de [a-z]. 
        # Esta regra apaga sumariamente QUALQUER linha do documento que contenha apenas uma única letra/número.
        markdown_body = re.sub(r'(?m)^\s*\w\s*$\n?', '', markdown_body)
        
        # Limpa o excesso de quebras de linha acumuladas pela fragmentação
        markdown_body = re.sub(r'\n{3,}', '\n\n', markdown_body)


        # 3. Anonimização (The Safety Layer)
        if self.redact:
            markdown_body = self._redact_pii(markdown_body)

        # 4. Estruturação JSONL
        title = clean_soup.title.string if clean_soup.title else "Sem Título"
        if title:
            title = unicodedata.normalize("NFKC", title)
            title = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u206f\xad\ufeff]', '', title)
            title = re.sub(r'\s+', ' ', title).strip()
        
        metadata_snapshot = {
            "source_title": title.strip() if title else "Sem Título",
            "source_url": context.get('url') or context.get('base_url', ''),
        }
        
        dataset_entry = {
            "metadata": {
                "source_url": context.get('url') or context.get('base_url'),
                "crawl_timestamp": datetime.now().isoformat(),
                "language_detected": "pt-BR", # TODO: Implementar detecção real se necessário
                "token_count_estimate": len(markdown_body.split()) // 0.75 # Estimativa rudimentar
            },
            "content": {
                "title": title.strip() if title else "",
                "markdown_body": markdown_body.strip(),
                "semantic_chunks": self._create_chunks(
                    markdown_body, 
                    chunk_size=1000, 
                    overlap=150, 
                    metadata_snapshot=metadata_snapshot
                )
            },
            "compliance": {
                "pii_filtered": self.redact,
                "gdpr_status": "compliant" if self.redact else "not_evaluated"
            }
        }

        context['dataset_entry'] = dataset_entry
        logger.info("✅ Dados destilados e prontos para exportação JSONL.")
        
        return context

    def _redact_pii(self, text: str) -> str:
        """Remove e-mails e telefones para conformidade GDPR."""
        # Email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)
        # Telefone (Brasil e Internacional genérico)
        text = re.sub(r'\+?\d{1,3}[\s-]?\(?\d{2,3}\)?[\s-]?\d{4,5}[\s-]?\d{4}', '[REDACTED_PHONE]', text)
        return text

    def _create_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 150, metadata_snapshot: dict = None) -> list:
        """
        Técnica de Janela Deslizante (Sliding Window) com Overlap e Quebra Semântica.
        Divide o texto para RAG garantindo que pedaços lógicos não percam contexto.
        """
        chunks = []
        start = 0
        chunk_id = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Preservação Semântica: Tenta não cortar palavras ou frases no meio
            if end < text_length:
                last_newline = chunk_text.rfind('\n')
                last_space = chunk_text.rfind(' ')
                # Prioriza quebra de linha (parágrafos), caso contrário, usa o último espaço
                break_point = last_newline if (last_newline > chunk_size * 0.7) else last_space
                
                if break_point > chunk_size * 0.5: # Só recua se não for truncar severamente o chunk
                    end = start + break_point
                    chunk_text = text[start:end]

            clean_chunk = chunk_text.strip()
            
            # Engenharia de Qualidade (Data Hygiene): Ignora chunks vazios ou ruidosos sem conteúdo real
            if len(clean_chunk) > 50:
                chunk_data = {
                    "id": chunk_id,
                    "text": clean_chunk,
                    "length": len(clean_chunk),
                    "vector_ready": True,
                    "metadata_snapshot": {
                        "token_estimate": len(clean_chunk) // 4 # Estimativa rápida (1 token ~ 4 chars)
                    }
                }
                
                # Metadata Inheritance: Chunk herda as propriedades do documento Pai
                if metadata_snapshot:
                    chunk_data["metadata_snapshot"].update(metadata_snapshot)
                    
                chunks.append(chunk_data)
                chunk_id += 1
                
            start = end - overlap # Avança considerando a sobreposição para costurar contexto
            
            # Prevenção estrutural: Garante que a janela avança mesmo se o texto for muito denso
            if start >= end:
                start = end

        return chunks
