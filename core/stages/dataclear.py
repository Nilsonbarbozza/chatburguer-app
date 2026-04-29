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

def run_dataclear_job(html_content: str, url: str, executor_level: str, 
                        config: Dict[str, Any], capture_id: str = None, 
                        mission_id: str = None) -> Dict[str, Any]:
    """
    Função global Picklable para ser executada no ProcessPoolExecutor.
    Recebe os dados brutos e a configuração da missão com metadados de linhagem.
    """
    from bs4 import BeautifulSoup
    
    # Instancia o stage localmente no processo secundário
    cleaner = DataClearStage(config=config)
    
    # Prepara o contexto com linhagem (Artifact-Oriented)
    soup = BeautifulSoup(html_content, 'lxml')
    context = {
        "soup": soup,
        "url": url,
        "executor_level": executor_level,
        "capture_id": capture_id,
        "mission_id": mission_id
    }
    
    # Executa a limpeza
    processed_context = cleaner.process(context)
    
    return {
        "dataset_entries": processed_context.get("dataset_entries", []),
        "waf_blocked": processed_context.get("waf_blocked", False)
    }

class DataClearStage(ProcessorStage):
    """
    Agente de limpeza e estruturação de dados (AgenteDataClear).
    Transforma o soup em um dataset JSONL otimizado.
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        self.archetype = self.config.get("archetype", "blog")
        self.fidelity_threshold = float(self.config.get("fidelity_threshold", 0.7)) # Aumentado para Gold Standard
        self.redact = self.config.get("redact_pii", "true").lower() == "true"

        # --- GOLD STANDARD SNIPER PATTERNS ---
        self.noise_titles = {
            'compartilhe isso:', 'share this:', 'share:', 'relacionado', 'related', 
            'related posts', 'leia também', 'veja também', 'você pode gostar',
            'posts recentes', 'recent posts', 'categorias', 'siga:', 'equipe dsa',
            'clique no link abaixo', 'responder', 'deixe uma resposta', 'comentários'
        }
        
        self.noise_selectors = [
            'script', 'style', 'nav', 'footer', 'aside', 'iframe', 'noscript', 
            'svg', 'canvas', 'video', 'audio', 'button', 'form', 'header',
            '.sharedaddy', '.jp-relatedposts', '.social-share', '.post-author',
            '.entry-footer', '.wpcnt', '#sharing_email', '.robots-nocontent',
            '.comments-area', '#respond', '.relatedposts', '.widget_related_posts_widget',
            '.post-navigation', '.author-bio', '.newsletter-box'
        ]

        self.url_blacklist_patterns = [
            r'/author/', r'/tag/', r'/categoria/', r'/category/', r'/page/\d+', r'/1970/'
        ]
        
        allowed_raw = self.config.get("allowed_domains", "*")
        self.allowed_domains = set(allowed_raw.split(",")) if allowed_raw != "*" else "*"

        # Stopwords de Navegação (Enterprise Signal)
        nav_stops_raw = self.config.get("nav_stopwords", "login,carrinho,checkout,search,menu,entrar,cadastrar,responder,comentar,feedback")
        self.nav_stopwords = set(nav_stops_raw.split(","))
        
        self.seen_fingerprints = set()

    def _sanitize_encoding(self, text: str) -> str:
        """Cura o Mojibake e normaliza o texto (Gold Standard Fix)."""
        if not text: return ""
        # 1. Normaliza caracteres Unicode (Ex: Ã -> A~)
        text = unicodedata.normalize('NFKC', text)
        # 2. Correção manual de Mojibake comum (Fallback)
        replacements = {
            "â€'": "'", "â€\"": "—", "â€œ": '"', "â€\x9d": '"',
            "â€¢": "•", "â€¦": "...", "Ã¡": "á", "Ã©": "é",
            "Ã\xad": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
            "Ã\xa3": "ã", "Ã\xb5": "õ", "Ã§": "ç", "Ã\x81": "Á",
            "Ã\x89": "É", "Ã\x8d": "Í", "Ã\x93": "Ó", "Ã\x9a": "Ú",
            "Ã\x91": "Ñ", "Ã\x83": "Ã", "Ã\x95": "Õ", "Ã\x87": "Ç",
            "\ufffd": " " # Remove o caractere de erro ''
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        
        # 3. Remove caracteres de controle invisíveis
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\r\t")
        return text

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

    def _calculate_fidelity_score(self, text: str, item_soup) -> float:
        """Enterprise Fidelity Scorer v4.3 (Gold Standard)."""
        if not text or len(text) < 150: return 0.0
        
        score = 0.5 # Base mais rigorosa
        text_lower = text.lower()
        words = text.split()
        
        # Penalidade por ruído remanescente (Finding #1)
        noise_hits = sum(1 for p in ['relacionado', 'equipe dsa', 'clique no link', 'responder'] if p in text_lower)
        if noise_hits > 0: score -= (noise_hits * 0.15)
        
        # --- BONIFICAÇÕES ---
        life_signals = [' é ', ' são ', ' com ', ' para ', ' por ', ' que ', ' onde ', ' como ', ' mas ', ' ou ']
        life_hits = sum(1 for s in life_signals if s in text_lower)
        if life_hits > 5: score += 0.25
        
        sentences = re.split(r'[.!?]', text)
        avg_sentence_len = len(words) / max(1, len(sentences))
        if avg_sentence_len > 15: score += 0.2
        
        punc_hits = len(re.findall(r'[.,!?;]', text))
        punc_ratio = punc_hits / len(words)
        if punc_ratio > 0.07: score += 0.15
        
        return max(0.0, min(1.0, score))

    def _is_content_url(self, url: str) -> bool:
        """Filtra padrões de URL que não são conteúdo real (Bug #2 Fix)."""
        for pattern in self.url_blacklist_patterns:
            if re.search(pattern, url):
                return False
        return True

    def _extract_title_geometrically(self, item_soup, container_soup):
        """Extração Restritiva: Título deve estar no topo (Finding #2)."""
        # Restrição Geométrica: Título REAL em blogs costuma estar no início do HTML
        html_str = str(item_soup)[:5000] # Analisa apenas os primeiros 5k chars do bloco
        
        for tag_name in ['h1', 'h2']:
            for tag in item_soup.find_all(tag_name):
                text = tag.get_text(strip=True)
                if len(text) < 10 or text.lower() in self.noise_titles: continue
                
                # Verifica se está no topo do código (heurística simples)
                if str(tag) not in html_str: continue 
                
                # Verifica área proibida
                parent_classes = ' '.join(tag.parent.get('class', [])) + str(tag.parent.get('id', ''))
                if any(w in parent_classes.lower() for w in ['related', 'widget', 'sidebar', 'footer', 'comment']):
                    continue
                
                return tag
        return None

    def _get_fingerprint(self, text: str) -> str:
        """Gera um MinHash simplificado para deduplicação zero-cost."""
        clean_text = re.sub(r'\W+', '', text.lower())[:200]
        return hashlib.md5(clean_text.encode()).hexdigest()

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"=== Batalhão Gold Standard: Refino de Elite ({self.archetype}) ===")
        
        soup = context.get('soup')
        if not soup: return context

        # 0. Limpeza Química Prévia (Enfraquecendo o Inimigo)
        for noise in self.noise_selectors:
            for scrap in soup.select(noise):
                scrap.decompose()

        # 1. Identificação de Canonicidade (Finding #3, #6)
        # GOLD RULE: Para blogs, forçamos o BLOCO DOMINANTE ÚNICO.
        raw_blocks = soup.find_all('article')
        if not raw_blocks:
            raw_blocks = soup.find_all(['div', 'section'], class_=re.compile(r'post|entry|article', re.I))

        content_blocks = []
        if raw_blocks:
            # Busca o bloco com mais densidade de texto (O Artigo)
            total_text_len = len(soup.get_text())
            block_lengths = [len(b.get_text()) for b in raw_blocks]
            max_len = max(block_lengths) if block_lengths else 0
            
            if self.archetype == 'blog' and max_len > 1000:
                idx_max = block_lengths.index(max_len)
                content_blocks = [raw_blocks[idx_max]]
                logger.debug(f"💎 Artigo Canônico detectado ({max_len} chars).")
            else:
                content_blocks = raw_blocks

        dataset_entries = []
        base_url = context.get('url', '')
        capture_id = context.get('capture_id', 'unknown')
        mission_id = context.get('mission_id', 'default')

        # 2. Destilação
        for block in content_blocks:
            from bs4 import BeautifulSoup
            item_soup = BeautifulSoup(str(block), 'lxml')
            
            # Título (Recalibrado)
            title_tag = self._extract_title_geometrically(item_soup, soup)
            s_title = title_tag.get_text(strip=True) if title_tag else (soup.title.string if soup.title else None)
            if s_title: s_title = self._sanitize_encoding(s_title)
            
            # Markdown Puro
            try:
                content_text = md_converter(str(item_soup), heading_style="ATX") if md_converter else item_soup.get_text()
            except:
                content_text = item_soup.get_text()

            # Cura de Mojibake e Ruído Final
            content_text = self._sanitize_encoding(content_text)
            
            # Remoção Cirúrgica de Padrões DSA/Relacionados (Finding #1)
            content_text = re.sub(r'###\s+\*Relacionado\*.*?(?=\n#|\n\n|$)', '', content_text, flags=re.DOTALL | re.IGNORECASE)
            content_text = re.sub(r'Equipe\s+DSA.*', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'\[Compartilhar.*?\]\(.*?\)', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'Adoraria\s+saber\s+sua\s+opinião.*', '', content_text, flags=re.IGNORECASE)
            
            # Fidelidade Gold
            fidelity_score = self._calculate_fidelity_score(content_text, item_soup)
            if fidelity_score < self.fidelity_threshold: continue

            # Chunks de Alta Pureza (Finding #5)
            metadata = {"title": s_title, "url": base_url}
            chunks = self._create_chunks(content_text, metadata_snapshot=metadata)
            
            if chunks:
                id_hash = hashlib.sha256(base_url.encode()).hexdigest()
                dataset_entries.append({
                    "id_hash": id_hash, "url": base_url, "capture_id": capture_id,
                    "mission_id": mission_id, "fidelity_score": round(fidelity_score, 3),
                    "data": {"title": s_title, "markdown_body": content_text, "semantic_chunks": chunks}
                })

        # Deduplicação Final (1 URL = 1 Registro)
        unique_entries = {e['url']: e for e in dataset_entries}.values()
        context['dataset_entries'] = list(unique_entries)
        
        logger.info(f"✅ Destilação Gold: {len(context['dataset_entries'])} registros puros.")
        return context

    def _redact_pii(self, text: str) -> str:
        """Anonimização PII Nível 4."""
        text = text.replace(r'\_', '_')
        # Ofuscação de e-mail básica
        text = re.sub(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]', text)
        return text

    def _create_chunks(self, text: str, metadata_snapshot: dict = None) -> list:
        """Geração de Fragmentos Semânticos de Ouro (Finding #5)."""
        raw_chunks = []
        # Chunkização por parágrafo para manter unidade semântica
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        
        chunk_id = 0
        for p in paragraphs:
            # Filtro de ruído de UI (Finding #5)
            if any(w in p.lower() for w in ['responder', 'comentar', 'clique aqui', 'inscreva-se']):
                continue
                
            raw_chunks.append({
                "id": chunk_id, "text": p, "length": len(p),
                "metadata_snapshot": metadata_snapshot or {}
            })
            chunk_id += 1
        return raw_chunks
