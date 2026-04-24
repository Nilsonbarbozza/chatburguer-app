"""
core/stages/dataclear.py
Stage especializado para destilação de dados e conformidade para LLMs/RAG.
"""
import re
import json
import logging
import hashlib
import unicodedata
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urlparse, urljoin
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
    def __init__(self, redact_pii: bool = True, strict: bool = False):
        self.redact = redact_pii
        self.strict = strict
        # Tags de ruído global (Removidas apenas no Refino Final para não perder blocos)
        self.noise_tags = [
            'script', 'style', 'nav', 'footer', 'aside',
            'iframe', 'noscript', 'svg', 'canvas', 
            'video', 'audio', 'button', 'form', 'header'
        ]

    def _detect_waf_honeypot(self, soup) -> bool:
        """Detector de Assinaturas de Bloqueio e Evasão."""
        waf_signatures = [
            "cloudflare", "ddos-guard", "captcha", "hcaptcha", 
            "access denied", "permission denied", "challenge-platform",
            "checking your browser", "security challenge", "sucuri"
        ]
        text_lower = soup.get_text().lower()
        for sig in waf_signatures:
            if sig in text_lower:
                return True
        return False

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"=== AgenteDataClear: Iniciando Refino Semântico (Redigir PII: {self.redact}) ===")
        
        soup = context.get('soup')
        if not soup:
            logger.error("Soup não encontrado no contexto. Pulando DataClearStage.")
            return context

        # 0. DETECTOR DE POTE DE MEL / WAF
        if self._detect_waf_honeypot(soup):
            logger.error("🚫 SEGURANÇA: WAF/Honeypot detectado! Abortando para proteção.")
            context['waf_blocked'] = True
            return context

        from bs4 import BeautifulSoup
        base_url = context.get('url') or context.get('base_url', '')
        domain = urlparse(base_url).netloc if base_url else "unknown"
        crawl_timestamp = datetime.now().isoformat()
        current_executor = context.get('executor_level', 'engine-aiohttp')

        # 1. Identificação de Blocos (Antes de qualquer limpeza destrutiva)
        content_blocks = soup.find_all('article')
        if not content_blocks or len(content_blocks) <= 1:
            content_blocks = soup.find_all(['div', 'section'], class_=re.compile(r'post|entry|article', re.I))

        dataset_entries = []

        # 2. Processamento por Célula (Arquitetura Isolada)
        if content_blocks and len(content_blocks) > 1:
            logger.info(f"💥 Explodindo listagem: {len(content_blocks)} blocos detectados.")
            
            for block in content_blocks:
                # Isolamos o bloco em uma nova sopa para evitar efeitos colaterais
                item_soup = BeautifulSoup(str(block), 'lxml')
                
                # A. Título
                title_tag = item_soup.find(['h1', 'h2', 'h3', 'a'], class_=re.compile(r'title|heading', re.I)) or item_soup.find(['h1', 'h2', 'h3'])
                s_title = title_tag.get_text(strip=True) if title_tag else None
                
                # B. Link
                link_tag = item_soup.find('a', href=True)
                if title_tag and title_tag.name == 'a': link_tag = title_tag
                s_url = link_tag['href'] if link_tag else base_url
                if s_url.startswith('/'): s_url = urljoin(base_url, s_url)

                # C. Limpeza Cirúrgica (Apenas na célula)
                for scrap in item_soup(['script', 'style', 'img', 'figure', 'noscript', 'button', 'iframe', 'header']):
                    scrap.decompose()
                
                # D. Texto/Markdown
                try:
                    if md_converter:
                        content_text = md_converter(str(item_soup), heading_style="ATX", bullets="-")
                    else:
                        content_text = item_soup.get_text(separator=' ')
                except:
                    content_text = item_soup.get_text(separator=' ')

                # E. Refino de Texto
                content_text = re.sub(r'\[CONSULTE MAIS INFORMAÇÃO\].*?\n', '', content_text, flags=re.IGNORECASE)
                content_text = re.sub(r'CONSULTE MAIS INFORMAÇÃO', '', content_text, flags=re.IGNORECASE)
                content_text = re.sub(r'\n{3,}', '\n\n', content_text).strip()

                if len(content_text) < 15:
                    continue

                if self.redact:
                    content_text = self._redact_pii(content_text)

                # F. Chunks e Entrada
                final_title = s_title or "Artigo Sem Título"
                id_hash = hashlib.sha256(f"{s_url}_{crawl_timestamp}".encode('utf-8')).hexdigest()
                metadata = {"source_title": final_title, "source_url": s_url}
                
                chunks = self._create_chunks(content_text, metadata_snapshot=metadata)
                if not chunks and len(content_text) >= 15:
                    chunks = [{"id": 0, "text": content_text, "length": len(content_text), "vector_ready": True, "metadata_snapshot": metadata}]

                if chunks:
                    dataset_entries.append({
                        "id_hash": id_hash, "url": s_url, "domain": domain, 
                        "crawl_timestamp": crawl_timestamp, "schema_version": "v2_batalhao",
                        "executor": current_executor,
                        "data": {"title": final_title, "markdown_body": content_text, "semantic_chunks": chunks},
                        "compliance": {"pii_filtered": self.redact, "gdpr_status": "compliant"}
                    })

            # Deduplicação por título
            seen = set()
            unique = []
            for e in dataset_entries:
                if e['data']['title'] not in seen:
                    unique.append(e)
                    seen.add(e['data']['title'])
            context['dataset_entries'] = unique
            
        else:
            # Caso de Página Única
            logger.info("📄 Processando como Página Única.")
            item_soup = BeautifulSoup(str(soup), 'lxml')
            for scrap in item_soup(self.noise_tags + ['img', 'figure']):
                scrap.decompose()
            
            content_text = md_converter(str(item_soup)) if md_converter else item_soup.get_text(separator=' ')
            content_text = content_text.strip()
            
            if self.redact: content_text = self._redact_pii(content_text)
            
            final_title = soup.title.string if soup.title else "Sem Título"
            id_hash = hashlib.sha256(f"{base_url}_{crawl_timestamp}".encode('utf-8')).hexdigest()
            metadata = {"source_title": final_title, "source_url": base_url}
            chunks = self._create_chunks(content_text, metadata_snapshot=metadata)

            context['dataset_entries'] = [{
                "id_hash": id_hash, "url": base_url, "domain": domain, 
                "crawl_timestamp": crawl_timestamp, "schema_version": "v2_batalhao",
                "executor": current_executor,
                "data": {"title": final_title, "markdown_body": content_text, "semantic_chunks": chunks},
                "compliance": {"pii_filtered": self.redact, "gdpr_status": "compliant"}
            }]

        logger.info(f"✅ Destilação Completa: {len(context.get('dataset_entries', []))} entradas válidas.")
        return context

    def _redact_pii(self, text: str) -> str:
        """Anonimização PII Nível 4."""
        text = text.replace(r'\_', '_')
        # Ofuscação de e-mail básica
        text = re.sub(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]', text)
        return text

    def _create_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 150, metadata_snapshot: dict = None) -> list:
        """Geração de Fragmentos para RAG."""
        chunks = []
        text = text.strip()
        if not text: return []
        
        start = 0
        chunk_id = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) > 20:
                chunks.append({
                    "id": chunk_id, "text": chunk_text, "length": len(chunk_text),
                    "vector_ready": True, "metadata_snapshot": metadata_snapshot or {}
                })
                chunk_id += 1
            start = end - overlap
            if start >= len(text) or chunk_size > len(text): break
            
        return chunks
