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
        self.fidelity_threshold = float(self.config.get("fidelity_threshold", 0.6))
        self.redact = self.config.get("redact_pii", "true").lower() == "true"

        # Novo: Blacklist expandida de títulos ruidosos (Bug #1 Fix)
        self.noise_titles = {
            'compartilhe isso:', 'share this:', 'share:', 
            'relacionado', 'related', 'related posts',
            'leia também', 'veja também', 'você pode gostar',
            'posts recentes', 'recent posts', 'categorias',
            'enviar por e-mail', 'siga:'
        }
        
        # Novo: Blacklist de padrões de URL (Bug #2 Fix)
        self.url_blacklist_patterns = [
            r'/author/', r'/tag/', r'/categoria/', r'/category/',
            r'/page/\d+', r'/1970/'
        ]
        
        # Novo: Domínios permitidos
        allowed_raw = self.config.get("allowed_domains", "*")
        self.allowed_domains = set(allowed_raw.split(",")) if allowed_raw != "*" else "*"

        # Tags de ruído global
        self.noise_tags = [
            'script', 'style', 'nav', 'footer', 'aside',
            'iframe', 'noscript', 'svg', 'canvas', 
            'video', 'audio', 'button', 'form', 'header'
        ]
        
        # Stopwords de Navegação (Enterprise Signal)
        nav_stops_raw = self.config.get("nav_stopwords", "login,carrinho,checkout,search,menu,entrar,cadastrar")
        self.nav_stopwords = set(nav_stops_raw.split(","))
        
        # Cache de Deduplicação Local (MinHash simplificado por processo)
        self.seen_fingerprints = set()

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

    def _extract_title(self, item_soup):
        """Extrai o título real filtrando ruído social (Bug #1)."""
        candidates = item_soup.find_all(['h1', 'h2', 'h3'])
        # Tenta também encontrar links com classe de título se não houver headings
        if not candidates:
            candidates = item_soup.find_all('a', class_=re.compile(r'title|heading', re.I))
            
        for tag in candidates:
            text = tag.get_text(strip=True)
            # Filtra títulos curtos ou que contenham termos de redes sociais
            if text.lower() not in self.noise_titles and len(text) > 5:
                return tag
        return None

    def _calculate_fidelity_score(self, text: str, item_soup) -> float:
        """
        Enterprise Fidelity Scorer (0.0 a 1.0) - Versão Gold-Positive.
        Busca o "Zero Falso Negativo" bonificando conteúdo rico.
        """
        if not text: return 0.0
        
        score = 0.6  # Começamos em uma base neutra (threshold padrão)
        text_lower = text.lower()
        words = text.split()
        if not words: return 0.0
        
        # --- PENALIDADES (Lixo Detection) ---
        
        # Sinal 1: Densidade de Navegação
        nav_hits = sum(1 for w in words if w in self.nav_stopwords)
        nav_ratio = nav_hits / len(words)
        if nav_ratio > 0.1: score -= (nav_ratio * 1.5)
        
        # Sinal 2: Densidade de Links (Bug #4 Evolution)
        link_hits = len(re.findall(r'\[.*?\]\(.*?\)', text))
        link_ratio = link_hits / len(words)
        if link_ratio > 0.3: score -= 0.3
        
        # --- BONIFICAÇÕES (Gold Detection) ---
        
        # Sinal 3: Estabilidade Sintática e Verbos (Sinal de Vida)
        # Verbos comuns e conectivos indicam prosa real, não listas.
        life_signals = [' é ', ' são ', ' com ', ' para ', ' por ', ' que ', ' onde ', ' como ', ' mas ', ' ou ']
        life_hits = sum(1 for s in life_signals if s in text_lower)
        if life_hits > 3: score += 0.2 # Bônus de Proseidade
        
        # Sinal 4: Complexidade de Sentença
        # Conteúdo rico tem sentenças estruturadas (ponto final)
        sentences = re.split(r'[.!?]', text)
        avg_sentence_len = len(words) / max(1, len(sentences))
        if avg_sentence_len > 12: score += 0.15 # Bônus de Profundidade
        
        # Sinal 5: Pontuação Rica
        punc_hits = len(re.findall(r'[.,!?;]', text))
        punc_ratio = punc_hits / len(words)
        if punc_ratio > 0.06: score += 0.1 # Bônus de Articulação
        
        # Sinal 6: Entidades e Relevância (Archetype Specific)
        long_words = sum(1 for w in words if len(w) > 8)
        long_word_ratio = long_words / len(words)
        if long_word_ratio > 0.2: score += 0.1 # Bônus Técnico
        
        logger.debug(f"📊 Fidelity Audit: Score Final: {score:.2f} | NavRatio: {nav_ratio:.2f} | PuncRatio: {punc_ratio:.2f} | LifeHits: {life_hits} | LongWordRatio: {long_word_ratio:.2f}")
        return max(0.0, min(1.0, score))

    def _is_content_url(self, url: str) -> bool:
        """Filtra padrões de URL que não são conteúdo real (Bug #2 Fix)."""
        for pattern in self.url_blacklist_patterns:
            if re.search(pattern, url):
                return False
        return True

    def _extract_title_geometrically(self, item_soup, container_soup):
        """
        Title Extractor Enterprise v3.1: Prioridade Semântica + Visão de Raiz.
        """
        # 1. Prioriza H1 dentro de containers de conteúdo (Bug #1 Fix)
        for container_sel in ['article', 'main', '.post-content', '.entry-content']:
            # Verifica se o próprio item_soup é o container ou se está dentro dele
            is_match = False
            if container_sel.startswith('.'):
                classes = item_soup.get('class', [])
                if container_sel[1:] in classes: is_match = True
            elif item_soup.name == container_sel:
                is_match = True
            
            el = item_soup if is_match else (item_soup.find(container_sel) or item_soup.select_one(container_sel))
            
            if el:
                h1 = el.find('h1') or el.find('h2')
                if h1:
                    text = h1.get_text(strip=True)
                    if text.lower() not in self.noise_titles and len(text) > 8:
                        return h1

        # 2. Fallback Final: Busca qualquer H1-H3 no bloco inteiro (Bug #1 Final Fix)
        for tag_name in ['h1', 'h2', 'h3']:
            for tag in item_soup.find_all(tag_name):
                text = tag.get_text(strip=True)
                if len(text) < 8 or text.lower() in self.noise_titles: continue
                
                # Verifica se está em área proibida
                parent_classes = ' '.join(tag.parent.get('class', [])) + str(tag.parent.get('id', ''))
                if any(w in parent_classes.lower() for w in ['related', 'social', 'widget', 'sidebar', 'share', 'footer']):
                    continue
                
                return tag
                
        return None

    def _get_fingerprint(self, text: str) -> str:
        """Gera um MinHash simplificado para deduplicação zero-cost."""
        clean_text = re.sub(r'\W+', '', text.lower())[:200]
        return hashlib.md5(clean_text.encode()).hexdigest()

    def _extract_title(self, item_soup):
        # Mantido por retrocompatibilidade se necessário, mas agora usamos o geométrico
        return self._extract_title_geometrically(item_soup, None)

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"=== Batalhão Enterprise: Refino Adaptativo ({self.archetype}) ===")
        
        soup = context.get('soup')
        if not soup:
            logger.error("Soup não encontrado no contexto. Pulando DataClearStage.")
            return context

        # 0. DETECTOR DE POTE DE MEL / WAF
        if self._detect_waf_honeypot(soup):
            logger.error("🚫 SEGURANÇA: WAF/Honeypot detectado! Abortando para proteção.")
            context['waf_blocked'] = True
            return context

        # 0.1 EXTRAÇÃO DE TÍTULO GLOBAL (Sinal de Elite)
        # Extraímos antes de qualquer limpeza ou isolamento de blocos
        global_h1 = soup.find('h1')
        global_title = global_h1.get_text(strip=True) if global_h1 else (soup.title.string if soup.title else None)
        if global_title and (global_title.lower() in self.noise_titles or len(global_title) < 5):
            global_title = None # Invalida títulos ruidosos

        from bs4 import BeautifulSoup
        base_url = context.get('url') or context.get('base_url', '')
        domain = urlparse(base_url).netloc if base_url else "unknown"
        crawl_timestamp = datetime.now().isoformat()
        current_executor = context.get('executor_level', 'engine-aiohttp')
        capture_id = context.get('capture_id', 'unknown')
        mission_id = context.get('mission_id', 'default')

        # 1. Identificação de Blocos (Antes de qualquer limpeza destrutiva)
        # BUG FIX: Blogs modernos usam <article> para posts relacionados. 
        # Se houver um <article> muito grande e outros pequenos, NÃO é listagem.
        raw_blocks = soup.find_all('article')
        if not raw_blocks or len(raw_blocks) <= 1:
            raw_blocks = soup.find_all(['div', 'section'], class_=re.compile(r'post|entry|article', re.I))

        content_blocks = []
        if raw_blocks:
            if len(raw_blocks) > 1:
                # Heurística de Dominância: Se um bloco tem > 70% do texto total, ele é o ARTIGO ÚNICO.
                total_text_len = len(soup.get_text())
                block_lengths = [len(b.get_text()) for b in raw_blocks]
                max_len = max(block_lengths) if block_lengths else 0
                
                if max_len > (total_text_len * 0.6) or self.archetype == 'blog' and max_len > 2000:
                    # É um artigo único com "ruído" de posts relacionados.
                    idx_max = block_lengths.index(max_len)
                    content_blocks = [raw_blocks[idx_max]]
                    logger.debug(f"💎 Artigo Dominante detectado ({max_len} chars). Ignorando explosão de listagem.")
                else:
                    content_blocks = raw_blocks
            else:
                content_blocks = raw_blocks

        dataset_entries = []

        # 2. Processamento por Célula (Arquitetura Isolada)
        if content_blocks and len(content_blocks) > 1:
            logger.info(f"💥 Explodindo listagem: {len(content_blocks)} blocos detectados.")
            
            for block in content_blocks:
                # Isolamos o bloco em uma nova sopa para evitar efeitos colaterais
                item_soup = BeautifulSoup(str(block), 'lxml')
                
                # A. Título (Enterprise Geometry Fix)
                title_tag = self._extract_title_geometrically(item_soup, soup)
                s_title = title_tag.get_text(strip=True) if title_tag else None
                
                # B. Link (Prioriza o link do título ou com classe de título)
                link_tag = None
                if title_tag:
                    link_tag = title_tag.find('a', href=True) if title_tag.name != 'a' else title_tag
                
                if not link_tag:
                    link_tag = item_soup.find('a', class_=re.compile(r'title|entry', re.I), href=True)
                
                if not link_tag:
                    link_tag = item_soup.find('a', href=True) # Fallback

                s_url = link_tag['href'] if link_tag else base_url
                if s_url.startswith('/'): s_url = urljoin(base_url, s_url)
                
                # C. Filtro de Domínio e Padrões Enterprise (Bug #2 Fix)
                parsed_s_url = urlparse(s_url)
                if self.allowed_domains != "*" and parsed_s_url.netloc not in self.allowed_domains:
                    continue
                
                if not self._is_content_url(s_url):
                    logger.debug(f"🛑 BLOQUEADO: URL filtrada por padrão (autor/tag/page): {s_url}")
                    continue

                # C. Limpeza Cirúrgica (Apenas na célula)
                # Remove tags ruidosas e seletores de widgets sociais comuns
                noise_selectors = [
                    'script', 'style', 'img', 'figure', 'noscript', 'button', 'iframe', 'header',
                    '.sharedaddy', '.jp-relatedposts', '.social-share', '.post-author',
                    '.entry-footer', '.wpcnt', '#sharing_email', '.robots-nocontent'
                ]
                for scrap in item_soup(noise_selectors):
                    scrap.decompose()
                
                # Remove qualquer elemento que contenha "Compartilhe isso" no ID ou Classe
                for social_widget in item_soup.find_all(attrs={"class": re.compile(r'share|social|widget', re.I)}):
                    social_widget.decompose()
                
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
                
                # SNIPER UNIVERSAL: Mata blocos de compartilhamento social complexos e multilingues
                content_text = re.sub(r'\[Compartilhar|Share|Follow us.*?\]\(.*?\)', '', content_text, flags=re.DOTALL | re.IGNORECASE)
                content_text = re.sub(r'\(abre em nova janela|opens in new window\)', '', content_text, flags=re.IGNORECASE)
                content_text = re.sub(r'(?i)(Compartilhe|Share|Siga) (isso|this):.*?(?=###|##|#|\n\n|$)', '', content_text, flags=re.DOTALL)
                
                # Limpeza de resíduos de redes sociais (Universal)
                social_junk = ['Facebook', 'Twitter', 'LinkedIn', 'WhatsApp', 'Tumblr', 'Pinterest', 'Reddit', 'Instagram', 'Youtube']
                for sj in social_junk:
                    content_text = re.sub(f'(?i){sj}', '', content_text)

                content_text = re.sub(r'\n{3,}', '\n\n', content_text).strip()

                # TRINCHEIRA 3: ENTERPRISE FIDELITY SCORER
                fidelity_score = self._calculate_fidelity_score(content_text, item_soup)
                
                if fidelity_score < self.fidelity_threshold:
                    logger.debug(f"🛑 BLOQUEADO: Fidelidade Baixa ({fidelity_score:.2f} < {self.fidelity_threshold})")
                    continue

                # TRINCHEIRA 4: DEDUPLICAÇÃO ZERO-COST (MinHash)
                fingerprint = self._get_fingerprint(content_text)
                if fingerprint in self.seen_fingerprints:
                    logger.debug(f"🛡️ BLOQUEADO: Duplicata detectada (MinHash matching)")
                    continue
                self.seen_fingerprints.add(fingerprint)

                if len(content_text) < 300:
                    continue

                if self.redact:
                    content_text = self._redact_pii(content_text)

                # F. Chunks e Entrada
                final_title = s_title or global_title or "Artigo Sem Título"
                # O ID deve ser baseado apenas na URL para permitir deduplicação real
                id_hash = hashlib.sha256(f"{s_url}".encode('utf-8')).hexdigest()
                metadata = {"source_title": final_title, "source_url": s_url}
                
                chunks = self._create_chunks(content_text, metadata_snapshot=metadata)
                if not chunks and len(content_text) >= 15:
                    chunks = [{"id": 0, "text": content_text, "length": len(content_text), "vector_ready": True, "metadata_snapshot": metadata}]

                if chunks:
                    dataset_entries.append({
                        "id_hash": id_hash, "url": s_url, "domain": domain, 
                        "capture_id": capture_id, "mission_id": mission_id,
                        "fidelity_score": round(min(fidelity_score, 1.0), 3), # Persistência (Bug #4)
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
            
            # SNIPER (Página Única)
            content_text = re.sub(r'\[Compartilhar no.*?\]\(.*?\)', '', content_text, flags=re.DOTALL | re.IGNORECASE)
            content_text = re.sub(r'\(abre em nova janela\)', '', content_text, flags=re.IGNORECASE)
            content_text = re.sub(r'(?i)Compartilhe isso:.*?(?=###|##|#|\n\n|$)', '', content_text, flags=re.DOTALL)
            
            content_text = content_text.strip()
            
            if self.redact: content_text = self._redact_pii(content_text)
            
            final_title = global_title or (soup.title.string if soup.title else "Sem Título")
            # O ID deve ser baseado apenas na URL para permitir deduplicação real
            id_hash = hashlib.sha256(f"{base_url}".encode('utf-8')).hexdigest()
            metadata = {"source_title": final_title, "source_url": base_url}
            chunks = self._create_chunks(content_text, metadata_snapshot=metadata)

            context['dataset_entries'] = [{
                "id_hash": id_hash, "url": base_url, "domain": domain, 
                "capture_id": capture_id, "mission_id": mission_id,
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
        """Geração de Fragmentos Semânticos para RAG (Bug #3 Fix)."""
        chunks = []
        text = text.strip()
        if not text: return []
        
        start = 0
        chunk_id = 0
        while start < len(text):
            end = start + chunk_size
            
            # Tenta encontrar o fim de uma sentença para não cortar no meio (Bug #3)
            if end < len(text):
                # Procura delimitadores de sentença no final do chunk
                # rfind procura da direita para a esquerda em um range seguro
                found_delimiter = False
                for delimiter in ['\n\n', '. ', '.\n', '! ', '? ']:
                    # Procuramos o delimitador nos últimos 200 caracteres do limite planejado
                    pos = text.rfind(delimiter, start + (chunk_size // 2), end + 200)
                    if pos != -1:
                        end = pos + len(delimiter)
                        found_delimiter = True
                        break
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) > 20:
                chunks.append({
                    "id": chunk_id, "text": chunk_text, "length": len(chunk_text),
                    "vector_ready": True, "metadata_snapshot": metadata_snapshot or {}
                })
                chunk_id += 1
            
            # O próximo start deve respeitar o overlap baseado no 'end' real encontrado
            start = end - overlap
            if start >= len(text) or chunk_size > len(text): break
            
        return chunks
