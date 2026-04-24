import asyncio
import logging
import time
from typing import Tuple, Optional
from urllib.parse import urlparse
from protego import Protego
import aiohttp

logger = logging.getLogger("RobotsGuard")

class RobotsGuard:
    """
    O Filtro de Conformidade robots.txt do Batalhão.
    Implementa o modo "Good Bot" com override dinâmico para clientes.
    """
    
    DEFAULT_UA = "ChatBurguer-Batalhao/2.0 (+https://chatburguer.com.br/bot-policy)"

    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 86400  # 24 horas de cache para robots.txt

    async def _fetch_robots(self, domain: str) -> str:
        """Busca o arquivo robots.txt de um domínio via HTTP."""
        url = f"https://{domain}/robots.txt"
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": self.DEFAULT_UA}) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 404:
                        return "User-agent: *\nAllow: /"  # Sem robots = tudo liberado
                    return ""
        except Exception as e:
            logger.warning(f"Erro ao buscar robots.txt para {domain}: {e}")
            return ""

    async def _get_parser(self, domain: str) -> Optional[Protego]:
        """Obtém o parser do cache do Redis ou faz o fetch."""
        cache_key = f"robots_cache:{domain}"
        content = await self.redis.get(cache_key)
        
        if content is None:
            logger.info(f"🔍 Buscando robots.txt para o domínio: {domain}")
            content = await self._fetch_robots(domain)
            if content:
                await self.redis.set(cache_key, content, ex=self.cache_ttl)
            else:
                # Se falhar, assume liberado para não travar o crawler por erro de DNS/Network
                return Protego.parse("User-agent: *\nAllow: /")

        return Protego.parse(content)

    async def can_crawl(self, url: str, respect_robots: bool = True) -> Tuple[bool, str]:
        """
        Avalia se a URL pode ser processada.
        Retorna: (bool_pode_seguir, status_string)
        """
        # 1. Se o cliente optou por NÃO respeitar (Risco Jurídico assumido)
        if not respect_robots:
            logger.warning(f"⚖️ OVERRIDE: Cliente assumiu risco para {url}. Ignorando robots.txt.")
            return True, "BYPASSED_BY_CLIENT"

        # 2. Respeito Padrão ao Protocolo
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path or "/"
            
            parser = await self._get_parser(domain)
            if parser.can_fetch(self.DEFAULT_UA, url):
                return True, "ALLOWED"
            else:
                logger.error(f"🚫 BLOQUEIO ROBOTS: Acesso proibido pelo site em {url}")
                return False, "DISALLOWED"
                
        except Exception as e:
            logger.error(f"Erro ao validar robots.txt: {e}. Permitindo por segurança (fail-open).")
            return True, "ERROR_FALLBACK"
