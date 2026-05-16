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

import time
import signal
import os
from contextlib import contextmanager
from core.schemas.extraction import ExtractionMethod, DataClearResult, ExtractionResult

setup_logging()
logger = logging.getLogger('html_processor')

class ExtractionTimeout(Exception):
    pass

@contextmanager
def extraction_timeout(seconds: int):
    """
    Context manager de timeout via SIGALRM.
    Funciona apenas em Linux/Mac (ambiente de produção ECS).
    Trata graciosamente o AttributeError se o sinal SIGALRM não existir (ex: Windows).
    """
    def _handler(signum, frame):
        raise ExtractionTimeout(f"Extração excedeu {seconds}s")

    try:
        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
    except (AttributeError, ValueError):
        # Fallback para ambientes sem SIGALRM (Windows)
        yield
        return

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def _try_strategy(name: str, fn, *args) -> tuple[Optional[str], int]:
    """
    Executa uma estratégia de extração com isolamento completo.
    Retorna: (texto_extraido, tempo_ms) ou (None, tempo_ms) se falhar.
    """
    t0 = time.monotonic()
    try:
        result = fn(*args)
        elapsed = int((time.monotonic() - t0) * 1000)
        if result:
            logger.info(f"✅ [{name}] Sucesso em {elapsed}ms ({len(result)} chars)")
        return result, elapsed
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        logger.warning(f"⚠️ [{name}] Falhou em {elapsed}ms: {type(e).__name__}: {e}")
        return None, elapsed

def _semantic_quality_score(text: str, html: str = "") -> float:
    """
    Score de qualidade semântica com 3 sinais rápidos.
    Substitui len(text) < 500 como critério de validação.

    Sinais:
      1. Ratio texto/html       — detecta páginas ghost (shell JS vazio)
      2. Link density           — detecta páginas de navegação pura
      3. Paragraph density      — detecta conteúdo real vs. lixo estrutural
    """
    if not text or len(text) < 50:
        return 0.0

    score = 0.0

    # Sinal 1: Ratio texto/html (0.0 → 0.40)
    if html:
        ratio = len(text) / max(len(html), 1)
        if ratio >= 0.15:   score += 0.40
        elif ratio >= 0.08: score += 0.25
        elif ratio >= 0.03: score += 0.10

    # Sinal 2: Link density — penaliza páginas de nav pura (0.0 → 0.30)
    words       = text.split()
    # Busca por padrões de URL ou links densos
    link_words  = len(re.findall(r'https?://', text))
    link_density = link_words / max(len(words), 1)
    if link_density < 0.01:   score += 0.30
    elif link_density < 0.05: score += 0.15
    # link_density >= 0.05: não pontua

    # Sinal 3: Paragraph density — conteúdo real tem parágrafos (0.0 → 0.30)
    paragraphs = [p for p in text.split('\n\n') if len(p.strip()) > 70]
    if len(paragraphs) >= 5:   score += 0.30
    elif len(paragraphs) >= 2: score += 0.15
    elif len(paragraphs) >= 1: score += 0.05

    return round(min(score, 1.0), 3)

# Singleton por processo — inicializado uma vez por worker
_PROCESS_LOCAL_CLEANER: dict = {}

def _get_or_create_cleaner(config: dict) -> 'DataClearStage':
    """
    Retorna instância cacheada de DataClearStage por processo.
    Evita reinstanciação em cada job no ProcessPoolExecutor.
    """
    # Usamos o archetype como chave primária, se não houver config complexa
    config_key = str(sorted(config.items()))
    if config_key not in _PROCESS_LOCAL_CLEANER:
        logger.debug(f"[SINGLETON] Inicializando DataClearStage no processo {os.getpid()}")
        _PROCESS_LOCAL_CLEANER[config_key] = DataClearStage(config=config)
    return _PROCESS_LOCAL_CLEANER[config_key]

def run_dataclear_job(html_content: str, url: str, executor_level: str, 
                        config: Dict[str, Any], capture_id: str = None, 
                        mission_id: str = None) -> DataClearResult:
    """
    Função global Picklable para ser executada no ProcessPoolExecutor.
    Recebe os dados brutos e a configuração da missão com metadados de linhagem.
    """
    try:
        with extraction_timeout(seconds=30):
            fallback_count = 0
            total_ms = 0
            extraction_method = ExtractionMethod.FAILED
            texto_extraido = None
            
            # Tática 1: JSON-LD
            texto, ms = _try_strategy("JSON-LD", lambda c: md_converter(extract_article_from_json_ld(extract_json_ld(c))["articleBody"]) if md_converter and extract_article_from_json_ld(extract_json_ld(c)) and extract_article_from_json_ld(extract_json_ld(c)).get("articleBody") else None, html_content)
            total_ms += ms
            if texto:
                texto_extraido = texto
                extraction_method = ExtractionMethod.JSON_LD
            else:
                fallback_count += 1
                
                # Tática 2: NEXT-DATA
                texto, ms = _try_strategy("NEXT-DATA", lambda c: mine_text_from_json(extract_next_data(c)), html_content)
                total_ms += ms
                if texto:
                    texto_extraido = texto
                    extraction_method = ExtractionMethod.NEXT_DATA
                else:
                    fallback_count += 1
                    
                    # Tática 3: DOM (BeautifulSoup/Markdownify)
                    # Note: We still use the DataClearStage for the DOM strategy as it handles complex archetypes
                    t0_dom = time.monotonic()
                    cleaner = _get_or_create_cleaner(config)
                    
                    # Check quality of existing text before DOM fallback
                    quality = _semantic_quality_score(texto_extraido, html_content) if texto_extraido else 0.0
                    
                    if quality < 0.35:
                        if texto_extraido:
                            logger.warning(f"⚠️ [QUALITY] Score {quality} abaixo do threshold. Fallback para DOM.")
                        
                        soup = BeautifulSoup(html_content, 'lxml')
                        context = {
                            "soup": soup,
                            "url": url,
                            "executor_level": executor_level,
                            "capture_id": capture_id,
                            "mission_id": mission_id
                        }
                        processed_context = cleaner.process(context)
                        total_ms += int((time.monotonic() - t0_dom) * 1000)
                        
                        extraction_method = ExtractionMethod.DOM
                        dataset_entries = processed_context.get("dataset_entries", [])
                        waf_blocked = processed_context.get("waf_blocked", False)
                        hub_items = processed_context.get("hub_items", [])
                        
                        # Recalculate quality for the DOM result
                        texto_final = ""
                        if dataset_entries:
                            texto_final = dataset_entries[0].get("data", {}).get("markdown_body", "")
                        
                        final_quality = _semantic_quality_score(texto_final, html_content)
                        
                        # Metrics logging
                        logger.info(
                            f"📊 [METRICS] url={url} "
                            f"method={extraction_method.value} "
                            f"quality={final_quality} "
                            f"fallbacks={fallback_count} "
                            f"time={total_ms}ms "
                            f"chars={len(texto_final)}"
                        )
                        
                        return DataClearResult(
                            dataset_entries=dataset_entries,
                            extraction_method=extraction_method,
                            quality_score=final_quality,
                            extraction_time_ms=total_ms,
                            waf_detected=waf_blocked,
                            fallback_count=fallback_count,
                            hub_items=hub_items
                        )
                    else:
                        # Success via Tática 1 or 2 with high quality
                        # We still need to create chunks and structure the result
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
                        
                        logger.info(
                            f"📊 [METRICS] url={url} "
                            f"method={extraction_method.value} "
                            f"quality={quality} "
                            f"fallbacks={fallback_count} "
                            f"time={total_ms}ms "
                            f"chars={len(texto_extraido)}"
                        )
                        
                        return DataClearResult(
                            dataset_entries=dataset_entries,
                            extraction_method=extraction_method,
                            quality_score=quality,
                            extraction_time_ms=total_ms,
                            fallback_count=fallback_count
                        )

            # If we reached here without a result, it failed
            return DataClearResult(
                dataset_entries=[],
                extraction_method=ExtractionMethod.FAILED,
                quality_score=0.0,
                extraction_time_ms=total_ms,
                fallback_count=fallback_count
            )

    except ExtractionTimeout:
        logger.error(f"⏱️ [TIMEOUT] Job abortado após 30s para {url}")
        return DataClearResult(
            dataset_entries=[],
            extraction_method=ExtractionMethod.FAILED,
            quality_score=0.0,
            extraction_time_ms=30000,
            error="extraction_timeout"
        )
    except Exception as e:
        logger.error(f"❌ [CRITICAL-ERROR] Falha catastrófica no job para {url}: {e}")
        return DataClearResult(
            dataset_entries=[],
            extraction_method=ExtractionMethod.FAILED,
            quality_score=0.0,
            extraction_time_ms=0,
            error=str(e)
        )

class DataClearStage(ProcessorStage):
    """
    Agente de limpeza e estruturação de dados (AgenteDataClear).
    Transforma o soup em um dataset JSONL otimizado.
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        self.archetype = self.config.get("archetype", Archetype.BLOG) or Archetype.BLOG
        self.fidelity_threshold = float(self.config.get("fidelity_threshold", 0.6))
        self.redact = str(self.config.get("redact_pii", "true")).lower() == "true"

        self.AUCTION_SELECTORS = {
            'megaleiloes.com.br': ['.card.open', '.card-leilao', '.card'],
            'leilaovip.com.br':   ['.card-leilao', '.item-leilao'],
            'superbid.net':       ['.app-auction-card', '.card'],
            # --- PADRÃO SEMÂNTICO (fallback universal) ---
            'default': [
                '.card', '.card-leilao', '.lote-item', '.auction-item',
                'a[href*="/imovel/"]', 'a[href*="/lote/"]',
                'a[href*="/anuncio/"]', 'a[href*="/bem/"]',
                'a[href*="/produto/"]', 'a[href*="/item/"]',
                '[class*="card"]', '[class*="lote"]',
                '[class*="imovel"]', '[class*="auction"]',
                'article', 'li.item',
            ],

            # ── JÁ MAPEADOS (mantidos) ──
            'megaleiloes.com.br':    ['.card', '.crd-item', 'a[href*="/anuncio/"]'],
            'leilaovip.com.br':      ['.card-anuncio', '.item-leilao', '.card'],
            'sodresantoro.com.br':   ['.shadow-1', '.bg-surface-container-low', 'a[class*="wrapper"]'],
            'portalzuk.com.br':      ['.card-leilao', '.rounded-xl'],

            # ── NOVOS: GRANDES PLAYERS ──
            'superbid.net':              ['.product-card', '.auction-item', '[class*="lot-card"]'],
            'gehring.com.br':            ['.item-leilao', '.card-item', 'a[href*="/lote/"]'],
            'lance.com.br':              ['.card-auction', '.property-card', '[class*="card-imovel"]'],
            'zuk.com.br':                ['.card-property', '.property-item', '[data-type="imovel"]'],
            'vectus.com.br':             ['.imovel-card', 'a[href*="/imovel/"]', '[class*="property"]'],
            'frazao.com.br':             ['.card-lote', '.lot-item', 'article.item'],
            'alexleiloes.com.br':        ['.product-item', '.card-lote', 'a[href*="/produto/"]'],
            'sold.com.br':               ['.auction-card', '.item-card', '[class*="lote"]'],

            # ── INSTITUCIONAIS ──
            'leiloesjudiciais.com.br':   ['[class*="processo"]', 'a[href*="/processo/"]', '.card-processo'],
            'leilaoimoveis.com.br':      ['.imovel-item', '.card-imovel', 'a[href*="/imovel/"]'],
            'caixa.gov.br':              ['.imovel', '[class*="card-imovel"]', 'a[href*="/imovel/"]'],
            'bancodobrasil.com.br':      ['.card-bem', '[class*="bem-leilao"]', 'a[href*="/bem/"]'],
        }

        self.TIPO_IMOVEL_MAP = {
            'casa':         ['casa', 'residência', 'residencia', 'sobrado'],
            'apartamento':  ['apartamento', 'apto', 'flat', 'studio', 'cobertura'],
            'terreno':      ['terreno', 'lote', 'área', 'gleba'],
            'comercial':    ['sala', 'loja', 'galpão', 'galpao', 'prédio', 'predio', 'comercial'],
            'rural':        ['fazenda', 'sítio', 'sitio', 'chácara', 'chacara', 'rural'],
        }

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

    def _get_selectors(self, url: str) -> list:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        return self.AUCTION_SELECTORS.get(domain, self.AUCTION_SELECTORS['default'])

    def _classify_tipo_imovel(self, text: str) -> str:
        text_lower = text.lower()
        for tipo, keywords in self.TIPO_IMOVEL_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return tipo
        return 'outros'

    def _extract_image(self, tag) -> Optional[str]:
        """
        Sniper Persistent V7: Total War (Regex-Based Deep Harvest).
        Captura qualquer URL de imagem que pareça real dentro do HTML do card.
        """
        blacklist = ['bank_icons', 'logo', 'itau', 'bradesco', 'santander', 'caixa', 'banco', 'institucional', 'avatar', 'placeholder', 'blank', 'pixel', 'spacer']
        
        # 1. Extração via Regex no HTML bruto do card (Poder total)
        card_html = str(tag)
        # Regex busca por extensões de imagem comuns em aspas ou atributos
        img_urls = re.findall(r'["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp|gif|bmp)(?:\?[^"\']*)?)["\']', card_html, re.I)
        
        # Filtra e prioriza a primeira que não esteja na blacklist
        for url in img_urls:
            url_clean = url.replace('&quot;', '').replace('&amp;', '&')
            if not any(word in url_clean.lower() for word in blacklist):
                # Priorizamos URLs que contenham 'batches' ou 'anuncios' (padrão MegaLeilões)
                if 'batches' in url_clean or 'anuncios' in url_clean:
                    return url_clean
        
        # 2. Se não achou com 'batches', pega a primeira limpa que sobrar
        for url in img_urls:
            if not any(word in url.lower() for word in blacklist):
                return url
            
        return None

    def _check_tag_for_image(self, tag) -> Optional[str]:
        """Auxiliar para validar uma tag específica com Blacklist agressiva."""
        # Blacklist de Logos Institucionais
        blacklist = ['bank_icons', 'logo', 'itau', 'bradesco', 'santander', 'caixa', 'banco', 'institucional', 'avatar', 'placeholder']
        
        # Check Style (Prioridade em Leilões)
        style = tag.get('style', '')
        if 'background-image' in style:
            bg_match = re.search(r'url\s*\(\s*["\']?([^"\']+)["\']?\s*\)', style)
            if bg_match:
                img_url = bg_match.group(1).replace('&quot;', '').replace('&amp;', '&')
                if not any(word in img_url.lower() for word in blacklist):
                    return img_url
        
        # Check attributes
        for attr in ['src', 'data-src', 'data-lazy', 'data-original', 'data-lazy-src', 'data-image']:
            val = tag.get(attr, '').strip()
            if val and val.startswith('http'):
                val_lower = val.lower()
                if any(word in val_lower for word in blacklist):
                    logger.debug(f"🚫 [SNIPER-IGNORE] Logo detectado: {val_lower}")
                    continue
                return val
        return None

    def _extract_auction_grid_items(self, soup, url: str) -> list:
        import time
        t0 = time.time()
        items = []
        selectors = self._get_selectors(url)
        
        cards = []
        for sel in selectors:
            cards.extend(soup.select(sel))
            
        seen = set()
        cards_dedup = []
        for c in cards:
            if not hasattr(c, 'name') or c.name is None: continue 
            cid = id(c)
            if cid not in seen:
                seen.add(cid)
                cards_dedup.append(c)
        cards = cards_dedup

        # FALLBACK SEMÂNTICO — ativa quando todos os seletores falharam
        if not cards:
            logger.warning(f"[AUCTION] 0 cards via seletores CSS para {url}. Ativando fallback semântico.")
            candidates = soup.find_all(['div', 'li', 'article', 'a'], limit=500)  # teto de varredura
            for c in candidates:
                text = c.get_text()
                money_hits = len(re.findall(r'R\$\s*[\d.,]+', text))
                has_link = c.find('a', href=True) or (c.name == 'a' and c.get('href'))
                if money_hits >= 1 and has_link and 50 < len(text) < 2000:
                    cards.append(c)
            logger.info(f"[AUCTION] Fallback semântico encontrou {len(cards)} candidatos.")

        base_url = self.config.get("base_url", url)

        for card in cards:
            text_content = card.get_text(separator=' ', strip=True)
            if len(text_content) < 30:
                continue

            # RegEx para valor (captura o primeiro)
            val_match = re.search(r'R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?', text_content)
            valor = val_match.group(0) if val_match else None

            # RegEx para datas
            dates = re.findall(r'\d{2}/\d{2}/\d{4}(?:\s*(?:às|as)?\s*\d{2}:\d{2})?', text_content)

            # Classificação
            tipo_imovel = self._classify_tipo_imovel(text_content)

            # Link vital (Fix href="#")
            href = None
            valid_links = []
            
            if card.name == 'a' and card.has_attr('href'):
                a_href = card.get('href', '').strip()
                if a_href and not a_href.startswith('#') and not a_href.lower().startswith(('javascript:', 'tel:', 'mailto:')):
                    valid_links.append((len(card.get_text(strip=True)), a_href))
                    
            for a_tag in card.find_all('a', href=True):
                a_href = a_tag.get('href', '').strip()
                if a_href and not a_href.startswith('#') and not a_href.lower().startswith(('javascript:', 'tel:', 'mailto:')):
                    text_len = len(a_tag.get_text(strip=True))
                    # Check if it has an image inside
                    if a_tag.find('img'):
                        text_len += 100 # weight images higher
                    valid_links.append((text_len, a_href))
            
            if valid_links:
                valid_links.sort(reverse=True, key=lambda x: x[0])
                href = valid_links[0][1]
            else:
                # Fallback to onclick regex
                card_html = str(card)
                onclick_match = re.search(r'''onclick\s*=\s*["'](?:window\.)?location(?:\.href)?\s*=\s*['"]([^'"]+)['"]''', card_html, re.I)
                if onclick_match:
                    href = onclick_match.group(1).strip()
            
            if href:
                href = urljoin(base_url, href)

            # Enriquecimento
            text_lower = text_content.lower()
            
            # Status Leilão
            status_leilao = None
            for status in ['aberto para lances', 'encerrado', 'em breve', 'sustado', 'arrematado', 'vendido', 'cancelado']:
                if status in text_lower:
                    status_leilao = status.title()
                    break
                    
            # Área/Metragem
            area_metragem = None
            area_match = re.search(r'([\d.,]+)\s*(?:m²|m2|ha|hectare|alqueire)s?', text_lower)
            if area_match:
                area_metragem = area_match.group(0)
                
            # Cômodos
            comodos = {}
            for comod in ['quarto', 'dorm', 'vaga', 'suite']:
                c_match = re.search(rf'(\d+)\s*{comod}s?', text_lower)
                if c_match:
                    comodos[f"{comod}s"] = int(c_match.group(1))
            
            # Tipo Judicial
            tipo_judicial = None
            if 'extrajudicial' in text_lower:
                tipo_judicial = 'Extrajudicial'
            elif 'judicial' in text_lower:
                tipo_judicial = 'Judicial'
                
            # Imagem vital (Sniper V7: Total War)
            img_src = self._extract_image(card)
                
            # Skip cards with no vital data
            if not valor and not href:
                continue

            items.append({
                "status_leilao": status_leilao,
                "tipo_judicial": tipo_judicial,
                "tipo_imovel": tipo_imovel,
                "valor": valor,
                "datas_leilao": dates,
                "area_metragem": area_metragem,
                "comodos": comodos if comodos else None,
                "links_vital": {"href": href, "image": img_src},
                "texto_bruto": text_content # Texto completo para a refinaria
            })

        logger.info(f"✅ [AUCTION-GRID] Extração bruta: {len(items)} cards em {time.time()-t0:.2f}s")
        
        # --- ALGORITMO ANTI-LOGO (Frequência Dinâmica) ---
        if items:
            from collections import Counter
            img_counts = Counter(it.get("links_vital", {}).get("image") for it in items if it.get("links_vital", {}).get("image"))
            
            # Threshold de ruído agressivo: em leilões fotos são únicas. Repetiu > 2 é logo.
            noise_threshold = 2
            noise_images = {img for img, count in img_counts.items() if count > noise_threshold}
            
            if noise_images:
                logger.warning(f"🚫 [ANTI-LOGO] Detectadas {len(noise_images)} imagens de ruído por repetição excessiva.")
                for it in items:
                    if it.get("links_vital", {}).get("image") in noise_images:
                        it["links_vital"]["image"] = None # Remove o ruído do dataset final

        return items

    def _detect_waf_honeypot(self, soup) -> tuple[bool, Optional[str]]:
        """
        Detecta assinaturas de WAF conhecidos.
        Retorna: (bloqueado: bool, vendor: str | None)
        """
        html_lower = str(soup).lower()
        text_lower = soup.get_text().lower()

        waf_signatures = {
            "cloudflare":   ["cloudflare", "cf-ray", "just a moment", "__cf_bm"],
            "datadome":     ["datadome", "dd_referrer", "datadome.co"],
            "perimeterx":   ["perimeterx", "_pxhd", "px-captcha"],
            "akamai":       ["akamai", "_abck", "bm_sz"],
            "imperva":      ["incapsula", "visid_incap", "imperva"],
            "sucuri":       ["sucuri", "sucuri-cloudproxy"],
            "generic":      ["access denied", "403 forbidden", "security challenge",
                             "captcha", "hcaptcha", "recaptcha", "robot check"],
        }

        for vendor, signatures in waf_signatures.items():
            # Checa no HTML completo (headers injetados) e no texto visível
            if any(sig in html_lower or sig in text_lower for sig in signatures):
                logger.warning(f"🚨 [WAF-{vendor.upper()}] Bloqueio detectado.")
                return True, vendor

        return False, None

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
        waf_blocked, waf_vendor = self._detect_waf_honeypot(soup)
        if waf_blocked:
            logger.warning(f"🚨 [WAF-DETECT] Honeypot/Bloqueio {waf_vendor} detectado em {base_url}")
            context['waf_blocked'] = True
            context['waf_vendor']  = waf_vendor
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

        # ROTA AUCTION GRID (V3 Enterprise Sniper)
        current_arch = str(self.archetype).lower()
        if "auction_grid" in current_arch:
            logger.info("🎯 [AUCTION-GRID-V3] Ativando Sniper V4 + Refinaria...")
            # 1. Extração Bruta Sniper V4
            raw_items = self._extract_auction_grid_items(soup, base_url)
            
            # 2. Refino de Elite
            from core.stages.auction_dataclear import AuctionDataClear
            handler = AuctionDataClear(self.config)
            return handler.process_auction(raw_items, base_url, context)

        # LIMPEZA
        for noise in self.noise_selectors:
            for scrap in soup.select(noise): scrap.decompose()

        # CANONICIDADE
        raw_blocks = soup.find_all('article')
        if not raw_blocks:
            raw_blocks = soup.find_all(['div', 'section', 'main'], class_=re.compile(r'post|entry|article|content|main|body|exm_|paragraph', re.I))
        
        logger.info(f"🔍 [DEBUG-ARTICLE] Blocos brutos encontrados: {len(raw_blocks)}")
        
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
                
                href_raw = (a.get('href') or '').strip()
                href_cmp = href_raw.lower()

                if not href_cmp or href_cmp.startswith('#'):
                    continue
                if any(href_cmp.startswith(s) for s in bad_schemes):
                    continue
                if any(kw in (title_text + ' ' + href_cmp) for kw in negative_keywords):
                    continue
                
                href = urljoin(base_url, href_raw)
                
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
        logger.info(f" [HUB-MINER] Extração concluída: {len(final_items)} cards em {time.time()-t0:.2f}s")
        return final_items
