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
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from core.pipeline import ProcessorStage
from core.utils import setup_logging
from agentic_api.schemas import Archetype
from core.stages.advanced_miner import (
    extract_json_ld, extract_article_from_json_ld, 
    extract_next_data, mine_text_from_json
)
from bs4 import BeautifulSoup

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
    # --- INJEÇÃO OS-014: AUTÓPSIA DE DADOS ---
    texto_extraido = None
    
    # TÁTICA 1: Tenta o Cofre de SEO (JSON-LD)
    ld_blocks = extract_json_ld(html_content)
    if ld_blocks:
        article = extract_article_from_json_ld(ld_blocks)
        if article and article.get("articleBody"):
            logger.info(f"💎 [OS-014] Conteúdo extraído via JSON-LD para {url}")
            texto_extraido = article["articleBody"]
            if md_converter:
                texto_extraido = md_converter(texto_extraido)

    # TÁTICA 2: Tenta Hidratação Next.js
    if not texto_extraido:
        next_data = extract_next_data(html_content)
        if next_data:
            logger.info(f"🚀 [OS-014] Minerando dados via Next.js hydration para {url}")
            texto_extraido = mine_text_from_json(next_data)

    # TÁTICA 3: O Tradicional (BeautifulSoup/Markdownify)
    if not texto_extraido or len(texto_extraido) < 500:
        if texto_extraido:
            logger.warning(f"⚠️ [OS-014] Conteúdo minerado insuficiente ({len(texto_extraido)} chars). Usando fallback tradicional.")
        
        cleaner = DataClearStage(config=config)
        soup = BeautifulSoup(html_content, 'lxml')
        context = {
            "soup": soup,
            "url": url,
            "executor_level": executor_level,
            "capture_id": capture_id,
            "mission_id": mission_id
        }
        processed_context = cleaner.process(context)
        
        entries = processed_context.get("dataset_entries", [])
        if entries:
            texto_extraido = entries[0].get("data", {}).get("markdown_body", "")
    
    if texto_extraido and (not 'processed_context' in locals()):
        cleaner = DataClearStage(config=config)
        metadata = {"title": url, "url": url}
        chunks = cleaner._create_chunks(texto_extraido, metadata_snapshot=metadata)
        
        id_hash = hashlib.sha256(url.encode()).hexdigest()
        dataset_entries = [{
            "id_hash": id_hash,
            "url": url,
            "capture_id": capture_id,
            "mission_id": mission_id,
            "executor": executor_level,
            "fidelity_score": 1.0,
            "data": {"title": url, "markdown_body": texto_extraido, "semantic_chunks": chunks}
        }]
        return {
            "dataset_entries": dataset_entries,
            "waf_blocked": False
        }
    elif 'processed_context' in locals():
        return {
            "dataset_entries": processed_context.get("dataset_entries", []),
            "waf_blocked": processed_context.get("waf_blocked", False)
        }
    
    return {"dataset_entries": [], "waf_blocked": False}

class DataClearStage(ProcessorStage):
    """
    Agente de limpeza e estruturação de dados (AgenteDataClear).
    Transforma o soup em um dataset JSONL otimizado.
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        self.archetype = self.config.get("archetype", Archetype.BLOG)
        self.fidelity_threshold = float(self.config.get("fidelity_threshold", 0.6))
        self.redact = self.config.get("redact_pii", "true").lower() == "true"

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
            '#reply-title', '.comment-form', 'img', 'figure', 'picture', 'figcaption'
        ]

        self.url_blacklist_patterns = [
            r'/author/', r'/tag/', r'/categoria/', r'/category/', r'/page/\d+', r'/1970/'
        ]
        
        allowed_raw = self.config.get("allowed_domains", "*")
        self.allowed_domains = set(allowed_raw.split(",")) if allowed_raw != "*" else "*"

    def _sanitize_encoding(self, text: str) -> str:
        """Cura o Mojibake e normaliza o texto."""
        if not text: return ""
        try:
            if any(p in text for p in ["Ã¡", "Ã©", "Ã\xad", "Ã³", "Ãº", "Ã\xa3", "Ã§"]):
                text = text.encode('latin-1').decode('utf-8')
        except: pass
        text = unicodedata.normalize('NFKC', text)
        replacements = {
            "â€'": "'", "â€\"": "—", "â€œ": '"', "â€\x9d": '"',
            "â€¢": "•", "â€¦": "...", "Ã¡": "á", "Ã©": "é",
            "Ã\xad": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
            "Ã\xa3": "ã", "Ã\xb5": "õ", "Ã§": "ç", "Ã\x81": "Á",
            "Ã\x89": "É", "Ã\x8d": "Í", "Ã\x93": "Ó", "Ã\x9a": "Ú",
            "Ã\x91": "Ñ", "Ã\x83": "Ã", "Ã\x95": "Õ", "Ã\x87": "Ç", "\ufffd": " " 
        }
        for bad, good in replacements.items(): text = text.replace(bad, good)
        return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\r\t")

    def _detect_waf_honeypot(self, soup) -> bool:
        """Detector de Assinaturas de Bloqueio e Evasão."""
        waf_signatures = ["cloudflare", "ddos-guard", "captcha", "hcaptcha", "access denied", "security challenge", "sucuri"]
        text_lower = soup.get_text().lower()
        return any(sig in text_lower for sig in waf_signatures)

    def _calculate_fidelity_score(self, text: str, item_soup) -> float:
        """Enterprise Fidelity Scorer v4.4."""
        if not text or len(text) < 150: return 0.0
        score = 0.5 
        text_lower = text.lower()
        noise_patterns = ['relacionado', 'equipe dsa', 'clique no link', 'responder', 'comentar', 'compartilhar', 'newsletter']
        noise_hits = sum(1 for p in noise_patterns if p in text_lower)
        if noise_hits > 0: score -= (noise_hits * 0.05)
        life_signals = [' é ', ' são ', ' com ', ' para ', ' por ', ' que ', ' onde ', ' como ', ' mas ', ' ou ']
        life_hits = sum(1 for s in life_signals if s in text_lower)
        if life_hits > 5: score += 0.25
        sentences = re.split(r'[.!?]', text)
        avg_sentence_len = len(text.split()) / max(1, len(sentences))
        if avg_sentence_len > 15: score += 0.2
        return max(0.0, min(1.0, score))

    def _extract_title_geometrically(self, item_soup, container_soup):
        """Extração de Título."""
        html_str = str(item_soup)[:5000] 
        for tag_name in ['h1', 'h2']:
            for tag in item_soup.find_all(tag_name):
                text = tag.get_text(strip=True)
                if len(text) < 10 or text.lower() in self.noise_titles: continue
                if str(tag) not in html_str: continue 
                parent_classes = ' '.join(tag.parent.get('class', [])) + str(tag.parent.get('id', ''))
                if any(w in parent_classes.lower() for w in ['related', 'widget', 'sidebar', 'footer', 'comment']): continue
                return tag
        return None


    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"=== Batalhão Gold Standard: Refino de Elite ({self.archetype}) ===")
        soup = context.get('soup')
        if not soup: return context
        base_url = context.get('url', '')

        # DETECÇÃO DE WAF (CRÍTICO PARA PRODUÇÃO)
        if self._detect_waf_honeypot(soup):
            logger.warning(f"🚨 [WAF-DETECT] Honeypot/Bloqueio detectado em {base_url}")
            context['waf_blocked'] = True
            context['dataset_entries'] = []
            return context
        
        context['waf_blocked'] = False

        # ROTA HUB
        if self.archetype == Archetype.HUB:
            hub_items = self._extract_hub_items(soup)
            context['dataset_entries'] = [{
                "id_hash": hashlib.sha256(base_url.encode()).hexdigest(),
                "url": base_url, 
                "capture_id": context.get('capture_id', 'unknown'),
                "mission_id": context.get('mission_id', 'default'),
                "executor": context.get('executor_level', 'unknown'),
                "fidelity_score": 1.0,
                "data": {
                    "title": str(soup.title.string) if soup.title else base_url,
                    "markdown_body": f"Hub extraído: {len(hub_items)} itens.",
                    "semantic_chunks": [], "hub_items": hub_items
                }
            }]
            return context

        # LIMPEZA
        for noise in self.noise_selectors:
            for scrap in soup.select(noise): scrap.decompose()

        # CANONICIDADE
        raw_blocks = soup.find_all('article')
        if not raw_blocks:
            raw_blocks = soup.find_all(['div', 'section', 'main'], class_=re.compile(r'post|entry|article|content|main|body|exm_|paragraph', re.I))

        content_blocks = raw_blocks if self.archetype != Archetype.BLOG else [max(raw_blocks, key=lambda b: len(b.get_text()))] if raw_blocks else []
        dataset_entries = []
        for block in content_blocks:
            item_soup = BeautifulSoup(str(block), 'lxml')
            title_tag = self._extract_title_geometrically(item_soup, soup)
            s_title = title_tag.get_text(strip=True) if title_tag else (str(soup.title.string) if (soup.title and soup.title.string) else None)
            if s_title: s_title = self._sanitize_encoding(s_title)
            try:
                content_text = md_converter(
                    str(item_soup),
                    heading_style="ATX",
                    strip=['a', 'img', 'figure']
                ) if md_converter else item_soup.get_text(separator='\n', strip=True)
            except Exception:
                content_text = item_soup.get_text(separator='\n', strip=True)
            content_text = self._sanitize_encoding(content_text)
            content_text = re.sub(r'!\[.*?\]\(.*?\)', '', content_text)
            fidelity_score = self._calculate_fidelity_score(content_text, item_soup)
            if fidelity_score < self.fidelity_threshold: continue
            chunks = self._create_chunks(content_text, metadata_snapshot={"title": s_title, "url": base_url})
            if chunks:
                dataset_entries.append({
                    "id_hash": hashlib.sha256(base_url.encode()).hexdigest(),
                    "url": base_url, "fidelity_score": round(fidelity_score, 3),
                    "data": {"title": s_title, "markdown_body": content_text, "semantic_chunks": chunks}
                })
        context['dataset_entries'] = list({e['url']: e for e in dataset_entries}.values())
        return context

    def _create_chunks(self, text: str, metadata_snapshot: dict = None) -> list:
        raw_chunks = []
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        for idx, p in enumerate(paragraphs):
            if any(re.search(rf"\b{w}\b", p.lower()) for w in ['responder', 'comentar', 'clique aqui', 'inscreva-se', 'compartilhe']): continue
            raw_chunks.append({"id": idx, "text": p, "length": len(p), "metadata_snapshot": metadata_snapshot or {}})
        return raw_chunks

    def _extract_timestamp(self, container, soup_root=None) -> Optional[str]:
        # Nível 1: tag semântica dentro do próprio card
        time_tag = container.find(
            ['time', 'span', 'div'],
            class_=re.compile(r'date|time|published|timestamp|item-date|post-date', re.I)
        )
        if time_tag:
            return time_tag.get('datetime') or time_tag.get_text(strip=True)

        # Nível 2: meta tags no <head> (Open Graph / Schema.org)
        if soup_root:
            for meta_prop in ['article:published_time', 'og:updated_time', 'datePublished']:
                meta = soup_root.find('meta', property=meta_prop) or \
                       soup_root.find('meta', attrs={'name': meta_prop})
                if meta and meta.get('content'):
                    return meta['content']

        return None

    def _extract_hub_items(self, soup) -> list:
        """Extração de Elite com Filtro de Ruído e Heurística de Snippets."""
        import time
        t0 = time.time()
        hub_items = []
        links = soup.find_all('a', href=True)
        base_url = self.config.get("base_url", "")
        
        bad_schemes = ('mailto:', 'tel:', 'javascript:', 'whatsapp:', 'data:', 'blob:')
        negative_keywords = ['privacidade', 'termos', 'assinatura', 'login', 'contato', 'newsletter', 'sobre', 'anuncie', 'expediente', 'cookies', 'vagas']
        negative_keywords.extend([
            'calculadora', 'ferramenta', 'newsletter', 'assinatura',
            'entrar', 'assine', 'cadastre', 'login', 'busca', 'buscar',
            'tag/', '/autor/', '/colunista/', 'patrocinado', 'publicidade'
        ])
        
        for a in links:
            try:
                title_text = ""
                heading = a.find(['h1', 'h2', 'h3', 'h4'])
                if heading: title_text = heading.get_text(strip=True)
                else:
                    if any(c in ' '.join(a.get('class', [])).lower() for c in ['title', 'headline', 'card', 'link-post']): title_text = a.get_text(strip=True)
                    elif len(a.get_text(strip=True)) > 20: title_text = a.get_text(strip=True)
                if not title_text or len(title_text) < 10: continue
                
                href = a.get('href') or ''
                href = href.strip().lower()

                if not href or href.startswith('#'):
                    continue
                if any(href.startswith(s) for s in bad_schemes):
                    continue
                if any(kw in (title_text + ' ' + href).lower() for kw in negative_keywords):
                    continue
                
                href = urljoin(base_url, href)
                
                snippet = ""
                container = a.parent
                if container:
                    for candidate in container.find_all(['p', 'span'], limit=10):
                        text = candidate.get_text(strip=True)
                        if text and text != title_text and 15 < len(text) < 400 and "http" not in text:
                            if any(c in ' '.join(candidate.get('class', [])).lower() for c in ['description', 'summary', 'excerpt', 'resumo', 'subtitle', 'snippet']):
                                snippet = text; break
                            if not snippet and candidate.name == 'p': snippet = text
                    if not snippet and container.parent:
                        desc_block = container.parent.find(['p', 'div', 'span'], class_=re.compile(r'description|summary|excerpt|resumo|subtitle', re.I))
                        if desc_block and desc_block.get_text(strip=True) != title_text: snippet = desc_block.get_text(strip=True)
                
                hub_items.append({
                    "title": self._sanitize_encoding(title_text), 
                    "url": href, 
                    "snippet": self._sanitize_encoding(snippet[:400]),
                    "timestamp": self._sanitize_encoding(self._extract_timestamp(container, soup_root=soup)) if container else None
                })
            except Exception as e: logger.warning(f"Erro no hub item: {e}"); continue
        final_items = []
        seen_urls = set()
        for item in hub_items:
            if item['url'] not in seen_urls: seen_urls.add(item['url']); final_items.append(item)
        logger.info(f"✅ [HUB-MINER] Extração concluída: {len(final_items)} cards em {time.time()-t0:.2f}s")
        return final_items
