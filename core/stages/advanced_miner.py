import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

def extract_json_ld(html_content: str) -> List[Dict[str, Any]]:
    """Extrai todos os blocos JSON-LD de uma página HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    json_ld_blocks = []
    for script in soup.find_all('script', type='application/ld+json'):
        content = script.text or script.string
        if not content:
            continue
        try:
            data = json.loads(content.strip())
            if isinstance(data, list):
                json_ld_blocks.extend(data)
            else:
                json_ld_blocks.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return json_ld_blocks

def extract_article_from_json_ld(ld_blocks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Busca por esquemas de Artigo dentro dos blocos JSON-LD."""
    article_types = {'Article', 'NewsArticle', 'BlogPosting', 'Report', 'ScholarlyArticle'}
    
    for block in ld_blocks:
        # Pode ser um objeto direto ou um @graph
        if block.get('@type') in article_types:
            # Se não tiver articleBody, tenta descrição + headline como fallback
            if not block.get("articleBody") and block.get("description"):
                block["articleBody"] = f"{block.get('headline', '')}\n\n{block.get('description')}"
            return block
        
        if '@graph' in block:
            for item in block['@graph']:
                if item.get('@type') in article_types:
                    if not item.get("articleBody") and item.get("description"):
                        item["articleBody"] = f"{item.get('headline', '')}\n\n{item.get('description')}"
                    return item
    return None

def extract_next_data(html_content: str) -> Optional[Dict[str, Any]]:
    """Extrai o estado de hidratação Next.js (__NEXT_DATA__)."""
    soup = BeautifulSoup(html_content, 'html.parser')
    script = soup.find('script', id='__NEXT_DATA__')
    content = script.text if script else None
    if content:
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return None
    return None

def mine_text_from_json(data: Any) -> str:
    """Extrai recursivamente todo texto relevante de um objeto JSON (focado em Next.js props)."""
    texts = []
    
    def _recursive_extract(obj):
        if isinstance(obj, str):
            if len(obj) > 20: # Filtra ruídos curtos
                texts.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                _recursive_extract(item)
        elif isinstance(obj, dict):
            # Prioriza chaves conhecidas de conteúdo em Next.js
            content_keys = ['content', 'body', 'text', 'description', 'title', 'subTitle']
            for k, v in obj.items():
                if any(ck in k.lower() for ck in content_keys):
                    _recursive_extract(v)
                else:
                    # Continua a busca em outros campos mas sem prioridade
                    _recursive_extract(v)

    _recursive_extract(data)
    return "\n\n".join(texts)
