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
    def __init__(self, redact_pii: bool = True, strict: bool = False):
        self.redact = redact_pii
        self.strict = strict
        # Tags estruturais que não compõem conteúdo legível para o modelo
        self.noise_tags = [
            'script', 'style', 'nav', 'footer', 'header', 'aside',
            'iframe', 'noscript', 'svg', 'path', 'g', 'canvas', 
            'video', 'audio', 'button', 'form', 'section[role="complementary"]'
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
            
        # 1.5 The Cookie Monster (Destruição de DOM Invisível de GDPR)
        # Procura e destrói contêineres inteiros de políticas de cookies
        cookie_and_gdpr_patterns = re.compile(
            r'\b(cookie-consent|cookiebot|CybotCookiebotDialog|cookie-banner|cookie-notice|gdpr-banner|consent-banner|social-share|popup-overlay|modal-overlay)\b', 
            re.I
        )

        for tag in clean_soup.find_all(class_=cookie_and_gdpr_patterns):
            tag.decompose()

        # Destrói também tags por ID (muito comum no Cookiebot e OneTrust)
        for tag in clean_soup.find_all(id=cookie_and_gdpr_patterns):
            tag.decompose()

        # 1.6 Sniper de Ads e Sponsored Content
        ad_patterns = re.compile(r'\b(ad-container|sponsored|promoted|taboola|outbrain|related-content|trending)\b', re.I)
        for tag in clean_soup.find_all(class_=ad_patterns):
            tag.decompose()

        # 1.7 O "Cheat Code" Semântico (Extração de JSON-LD)
        # Portais como Reuters escondem o conteúdo limpo aqui.
        json_ld_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                js_content = json.loads(script.string)
                if isinstance(js_content, dict):
                    # Extraímos apenas o que é útil para contexto (Título, Descrição, Artigo)
                    useful = {
                        "headline": js_content.get("headline"),
                        "description": js_content.get("description"),
                        "articleBody": js_content.get("articleBody")
                    }
                    # Remove campos nulos
                    json_ld_data.append({k: v for k, v in useful.items() if v})
            except:
                continue

        # Isolamento Robusto de Main Content (Heurística de Densidade Cascata):
        # Evita a armadilha de honeypots ou divs de acessibilidade vazias (role="main") validando a densidade de bytes limpos.
        # Adicionamos seletores de elite para Blogs (entry-content, post-content)
        blog_content_patterns = re.compile(r'entry-content|post-content|article-content|main-content|post-text', re.I)
        
        candidates = [
            clean_soup.find('main'),
            clean_soup.find(attrs={'role': 'main'}),
            clean_soup.find(class_=blog_content_patterns),
            clean_soup.find('article')
        ]
        
        main_content = None
        for candidate in candidates:
            if candidate and len(candidate.get_text(strip=True)) > 200:
                main_content = candidate
                break
                
        # Se nenhuma âncora passar pelo teste de densidade, assume corpo defensivo.
        if not main_content:
            main_content = clean_soup.body if clean_soup.body else clean_soup

        # 2. Conversão para Markdown (The MD-Transformer)
        if md_converter:
            markdown_body = md_converter(
                str(main_content), 
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
        
        # --- PODA SEMÂNTICA (MODO STRICT) ---
        if self.strict:
            logger.info("[STRICT] Executando Poda Semântica de Elite...")
            markdown_body = self._semantic_pruning(markdown_body)

        # Anti-Ofuscação CSS (O "Sniper" de Letras Soltas):
        # Esta regra apaga sumariamente QUALQUER linha do documento que contenha apenas uma única letra/número.
        markdown_body = re.sub(r'(?m)^\s*\w\s*$\n?', '', markdown_body)
        
        markdown_body = re.sub(r'\n{3,}', '\n\n', markdown_body)

        # Filtro de UI Boilerplate (Descarte Direto de Ações de Tela)
        # Fundamental para SPAs que deixam os labels na tela (Google Maps)
        ui_noise_patterns = [
            r'Arraste para alterar\n?',
            r'Recolher painel lateral\n?',
            r'Mostrar teclado\n?',
            r'Ocultar teclado\n?',
            r'Fazer login\n?',
            r'Mostrar seu local\n?',
            r'Tipo de mapa\n?',
            r'Zoom\n?',
            r'Camadas\n?',
            r'Navegar para a frente\n?',
            r'Navegar para trás\n?'
        ]
        for pattern in ui_noise_patterns:
            markdown_body = re.sub(pattern, '', markdown_body, flags=re.IGNORECASE)

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
        
        chunks = self._create_chunks(
            markdown_body, 
            chunk_size=1000, 
            overlap=150, 
            metadata_snapshot=metadata_snapshot
        )

        # Montagem do Payload Final
        dataset_entry = {
            "metadata": {
                "source_url": context.get('url'),
                "crawl_timestamp": datetime.now().isoformat(),
                "language_detected": context.get('language', 'pt-BR'),
                "token_count_estimate": len(markdown_body.split()) * 1.3,
                "json_ld_context": json_ld_data if json_ld_data else None
            },
            "content": {
                "title": soup.title.string if soup.title else "Sem título",
                "markdown_body": markdown_body,
                "semantic_chunks": chunks
            },
            "compliance": {
                "pii_filtered": self.redact,
                "gdpr_status": "compliant"
            }
        }

        context['dataset_entry'] = dataset_entry
        logger.info("✅ Dados destilados e prontos para exportação JSONL.")
        
        return context

    def _semantic_pruning(self, text: str) -> str:
        """
        Executa poda agressiva de conteúdo editorial ruidoso (Markdown-centric).
        """
        # 1. SNIPER DE BLOCOS (O Bloco do WhatsApp da BBC e similares)
        # Muitas vezes o markdownify adiciona negrito ou links aos marcadores
        block_patterns = [
            # Bloco Whatsapp da BBC
            re.compile(r'\*\*\[No WhatsApp\].*?Fim do Whatsapp!', re.DOTALL | re.IGNORECASE),
            re.compile(r'\[Pule Whatsapp.*?\]\(.*?\).*?(Fim do Whatsapp!|#end-of-whatsapp)', re.DOTALL | re.IGNORECASE),
            # Bloco de recomendações/mais lidas
            re.compile(r'\[Pule Mais lidas.*?\]\(.*?\).*?(Fim do Mais lidas|#end-of-recommendations)', re.DOTALL | re.IGNORECASE),
            # Redes Sociais
            re.compile(r'Siga a BBC News Brasil no.*?\n', re.IGNORECASE)
        ]

        for pattern in block_patterns:
            text = re.sub(pattern, '\n', text)

        # 2. FOOTER KILL-SWITCH (Desativado para evitar falsos-positivos agressivos)
        # Em vez de cortar o texto, vamos apenas remover as seções de ruído no final se elas existirem.
        footer_triggers = [
            r'## Assista', 
            r'## Histórias relacionadas',
            r'## Tópicos relacionados',
            r'## Leia mais', 
            r'## Principais notícias',
            r'## Mais lidas'
        ]
        
        # Comentamos o corte bruto e mantemos apenas para análise futura se necessário
        # for trigger in footer_triggers:
        #     match = re.search(trigger, text, re.IGNORECASE)
        #     if match:
        #         logger.info(f"[STRICT] Kill-Switch evitado (apenas logado): {trigger}")
        #         # text = text[:match.start()].strip()
        #         break 

        # 3. Limpeza de 'Skip-links' residuais
        text = re.sub(r'\[Pule.*?\]\(.*?\)', '', text, flags=re.IGNORECASE)
        
        return text.strip()

    def _redact_pii(self, text: str) -> str:
        """
        Escudo PII Enterprise Nível 4: Conformidade GDPR/LGPD Global.
        Implementa sanitização prévia, whitelist de URLs e um arsenal de Regex tático.
        """
        # ---------------------------------------------------------
        # 1. PRÉ-PROCESSAMENTO: Correção de Conflitos do Markdownify
        # ---------------------------------------------------------
        # O Markdownify frequentemente escapa underscores (\_) para não confundir com itálico.
        # Isso quebra a leitura de e-mails como carlos\_diretoria@...
        # Esta linha desfaz o escape para que a Regex enxergue o e-mail real.
        text = text.replace(r'\_', '_')

        # ---------------------------------------------------------
        # 2. O ESCUDO DE URL (Whitelist Temporária Absoluta)
        # ---------------------------------------------------------
        # Captura links HTTP brutos ou dentro da sintaxe Markdown [texto](link)
        url_pattern = re.compile(r'https?://[^\s\)]+')
        urls_encontradas = url_pattern.findall(text)
        
        # Mascara as URLs temporariamente com um hash irreal para proteção total
        for i, url in enumerate(urls_encontradas):
            text = text.replace(url, f'__TOKEN_URL_BLINDADA_{i}__')

        # ---------------------------------------------------------
        # 3. OFUSCAÇÃO DE E-MAIL (Padrão Global Unicode)
        # ---------------------------------------------------------
        # Suporta domínios e nomes com acentos (ex: müller, logística)
        email_pattern = re.compile(r'[a-zA-Z0-9._%+\-À-ÿ]+@[a-zA-Z0-9.\-À-ÿ]+\.[a-zA-Z]{2,8}')
        text = email_pattern.sub('[REDACTED_EMAIL]', text)

        # ---------------------------------------------------------
        # 4. ARSENAL TÁTICO DE TELEFONES (Cobertura Mundial Refinada)
        # ---------------------------------------------------------
        # Ajustamos para exigir separadores ou símbolos, evitando colisão com IDs de produto.
        phone_patterns = [
            # TÁTICA 1: Formato Internacional (Exige + ou 00 no início)
            r'(?:\+|00)\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{2,5}[\s-]?\d{2,5}(?:[\s-]?\d{1,5})?',

            # TÁTICA 2: Toll-Free (Exige hífen ou espaço após o prefixo)
            r'\b(?:1-)?(?:0800|0300|800|888|877|866|900|080)[\s-]?\d{3,4}[\s-]?\d{3,4}\b',

            # TÁTICA 3: Nacional com Separadores (Para evitar IDs de 10-12 dígitos puros)
            # Se for apenas número sem parênteses ou traço, o sistema ignora como sendo um SKU/ID.
            r'\b(?:\(\d{2,3}\)|\d{2,3})[\s\-.]?9?\d{4}[\-.]\d{4}\b'
        ]

        # Executa as varreduras em sequência
        for pattern in phone_patterns:
            text = re.sub(pattern, '[REDACTED_PHONE]', text)

        # ---------------------------------------------------------
        # 5. RESTAURAÇÃO DA INTEGRIDADE ESTRUTURAL
        # ---------------------------------------------------------
        # Devolve as URLs originais intactas para o documento final
        for i, url in enumerate(urls_encontradas):
            text = text.replace(f'__TOKEN_URL_BLINDADA_{i}__', url)

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
