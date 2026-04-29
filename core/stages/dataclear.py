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
        self.fidelity_threshold = float(self.config.get("fidelity_threshold", 0.6)) # Calibragem Final Gold
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
            '.post-navigation', '.author-bio', '.newsletter-box',
            '#comments', '.comment-list', '.comment-respond', '.comment-reply-title',
            '.comment-metadata', '.comment-body', '.reply', '.comment-content',
            '.form-submit', '.navigation.comment-navigation', '.pingback',
            '#reply-title', '.comment-form'
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
        """Cura o Mojibake e normaliza o texto (Gold Standard Fix Nível 5)."""
        if not text: return ""
        
        # 1. Tenta recuperar texto que foi corrompido de UTF-8 para Latin-1
        try:
            # Se o texto contém padrões clássicos de Mojibake UTF-8 (Ã¡, Ã©, etc)
            if any(p in text for p in ["Ã¡", "Ã©", "Ã\xad", "Ã³", "Ãº", "Ã\xa3", "Ã§"]):
                text = text.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

        # 2. Normaliza caracteres Unicode
        text = unicodedata.normalize('NFKC', text)
        
        # 3. Correção manual de Mojibake residual
        replacements = {
            "â€'": "'", "â€\"": "—", "â€œ": '"', "â€\x9d": '"',
            "â€¢": "•", "â€¦": "...", "Ã¡": "á", "Ã©": "é",
            "Ã\xad": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
            "Ã\xa3": "ã", "Ã\xb5": "õ", "Ã§": "ç", "Ã\x81": "Á",
            "Ã\x89": "É", "Ã\x8d": "Í", "Ã\x93": "Ó", "Ã\x9a": "Ú",
            "Ã\x91": "Ñ", "Ã\x83": "Ã", "Ã\x95": "Õ", "Ã\x87": "Ç",
            "\ufffd": " " 
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        
        # 4. Remove caracteres de controle invisíveis
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
        """Enterprise Fidelity Scorer v4.4 (Gold Standard)."""
        if not text or len(text) < 150: return 0.0
        
        score = 0.5 
        text_lower = text.lower()
        words = text.split()
        
        # Penalidade severa por ruído de UI/Marketing
        noise_patterns = ['relacionado', 'equipe dsa', 'clique no link', 'responder', 'comentar', 'compartilhar', 'newsletter']
        noise_hits = sum(1 for p in noise_patterns if p in text_lower)
        if noise_hits > 0: score -= (noise_hits * 0.05)
        
        # --- BONIFICAÇÕES ---
        life_signals = [' é ', ' são ', ' com ', ' para ', ' por ', ' que ', ' onde ', ' como ', ' mas ', ' ou ']
        life_hits = sum(1 for s in life_signals if s in text_lower)
        if life_hits > 5: score += 0.25
        
        sentences = re.split(r'[.!?]', text)
        avg_sentence_len = len(words) / max(1, len(sentences))
        if avg_sentence_len > 15: score += 0.2
        
        return max(0.0, min(1.0, score))

    def _is_content_url(self, url: str) -> bool:
        """Filtra padrões de URL que não são conteúdo real."""
        for pattern in self.url_blacklist_patterns:
            if re.search(pattern, url):
                return False
        return True

    def _extract_title_geometrically(self, item_soup, container_soup):
        """Extração Restritiva: Título deve estar no topo."""
        html_str = str(item_soup)[:5000] 
        
        for tag_name in ['h1', 'h2']:
            for tag in item_soup.find_all(tag_name):
                text = tag.get_text(strip=True)
                if len(text) < 10 or text.lower() in self.noise_titles: continue
                if str(tag) not in html_str: continue 
                
                parent_classes = ' '.join(tag.parent.get('class', [])) + str(tag.parent.get('id', ''))
                if any(w in parent_classes.lower() for w in ['related', 'widget', 'sidebar', 'footer', 'comment']):
                    continue
                
                return tag
        return None

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"=== Batalhão Gold Standard: Refino de Elite ({self.archetype}) ===")
        
        soup = context.get('soup')
        if not soup: return context

        # 0. Limpeza Química Prévia (Enfraquecendo o Inimigo)
        for noise in self.noise_selectors:
            for scrap in soup.select(noise):
                scrap.decompose()

        # 0.1 Expurgo por Palavras-Chave de Interação (Finding #7)
        # Remove elementos que contenham APENAS palavras de UI, respeitando limites de palavra
        for text_noise in ["Responder", "Comentar", "Deixe uma resposta"]:
            # Busca strings que contenham a palavra isolada (ignora se for parte de outra palavra)
            for element in soup.find_all(string=re.compile(rf"^\s*{text_noise}\s*$", re.I)):
                if element.parent:
                    element.parent.decompose()

        # 1. Identificação de Canonicidade
        raw_blocks = soup.find_all('article')
        if not raw_blocks:
            raw_blocks = soup.find_all(['div', 'section'], class_=re.compile(r'post|entry|article', re.I))

        content_blocks = []
        if raw_blocks:
            block_lengths = [len(b.get_text()) for b in raw_blocks]
            max_len = max(block_lengths) if block_lengths else 0
            
            if self.archetype == 'blog' and max_len > 1000:
                idx_max = block_lengths.index(max_len)
                content_blocks = [raw_blocks[idx_max]]
            else:
                content_blocks = raw_blocks

        dataset_entries = []
        base_url = context.get('url', '')
        capture_id = context.get('capture_id', 'unknown')
        mission_id = context.get('mission_id', 'default')
        executor = context.get('executor_level', 'unknown')

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
            
            # EXTERMINADOR DE MARKETING v2.0
            content_text = re.sub(r'###\s+\*Relacionado\*.*?(?=\n#|\n\n|$)', '', content_text, flags=re.DOTALL | re.IGNORECASE)
            content_text = re.sub(r'Equipe\s+DSA.*', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'\[Compartilhar.*?\]\(.*?\)', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'Adoraria\s+saber\s+sua\s+opinião.*', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'Inscreva-se\s+em\s+nossa\s+newsletter.*', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'Clique\s+aqui\s+para\s+saber\s+mais.*', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'Deixe\s+um\s+comentário.*', '', content_text, flags=re.IGNORECASE)
            
            # Fidelidade Gold
            fidelity_score = self._calculate_fidelity_score(content_text, item_soup)
            if fidelity_score < self.fidelity_threshold: continue

            # Chunks de Alta Pureza
            metadata = {"title": s_title, "url": base_url}
            chunks = self._create_chunks(content_text, metadata_snapshot=metadata)
            
            if chunks:
                id_hash = hashlib.sha256(base_url.encode()).hexdigest()
                dataset_entries.append({
                    "id_hash": id_hash, 
                    "url": base_url, 
                    "capture_id": capture_id,
                    "mission_id": mission_id, 
                    "executor": executor,
                    "fidelity_score": round(fidelity_score, 3),
                    "data": {"title": s_title, "markdown_body": content_text, "semantic_chunks": chunks}
                })

        unique_entries = {e['url']: e for e in dataset_entries}.values()
        context['dataset_entries'] = list(unique_entries)
        return context

    def _create_chunks(self, text: str, metadata_snapshot: dict = None) -> list:
        """Geração de Fragmentos Semânticos de Ouro (Exterminando UI)."""
        raw_chunks = []
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        
        chunk_id = 0
        for p in paragraphs:
            # Filtro de ruído agressivo com Word Boundary (Finding #1, #7)
            p_lower = p.lower()
            if any(re.search(rf"\b{w}\b", p_lower) for w in ['responder', 'comentar', 'clique aqui', 'inscreva-se', 'compartilhe']):
                continue
                
            raw_chunks.append({
                "id": chunk_id, "text": p, "length": len(p),
                "metadata_snapshot": metadata_snapshot or {}
            })
            chunk_id += 1
        return raw_chunks
