import aiohttp
import asyncio
import logging
from urllib.parse import urlparse
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger("DefenseIntelligence")

class DefenseLevel(Enum):
    LEVEL_0 = 0 # No defense (aiohttp is fine)
    LEVEL_1 = 1 # Basic Cloudflare (needs curl_cffi basic)
    LEVEL_2 = 2 # Moderate / JS Challenge (needs curl_cffi impersonate)
    LEVEL_3 = 3 # Datadome / Advanced (needs Playwright DC IP)
    LEVEL_4 = 4 # PerimeterX / Akamai (needs Playwright Residential IP)

class DefenseIntelligence:
    """
    Camada 3.2: Sonar Estratégico.
    Mapeia a complexidade do WAF/Defesa do alvo antes de designar a tropa pesada.
    """
    def __init__(self, redis_manager, robots_guard: Optional['RobotsGuard'] = None):
        self.rm = redis_manager
        self.robots_guard = robots_guard

    @staticmethod
    def extract_domain(url: str) -> str:
        try:
            return urlparse(url).netloc
        except Exception:
            return "unknown"

    async def classify_url(self, url: str, respect_robots: bool = True) -> Tuple[DefenseLevel, str]:
        """
        Avalia compliance e defesa. 
        Retorna: (DefenseLevel, compliance_status)
        """
        # 1. Verificação Pre-Flight de Robots.txt
        compliance_status = "ALLOWED"
        if self.robots_guard:
            allowed, compliance_status = await self.robots_guard.can_crawl(url, respect_robots=respect_robots)
            if not allowed:
                return DefenseLevel.LEVEL_0, "DISALLOWED" # Aborta (nível irrelevante se negado)

        # 2. Cache de Defesa (WAF)
        domain = self.extract_domain(url)
        cached_level = await self.rm.client.hget("defense_cache", domain)
        
        if cached_level is not None:
            return DefenseLevel(int(cached_level)), compliance_status
        
        # 3. Disparo do Probe
        level = await self._run_probe(url)
        
        # Grava nivel no cache por 24h
        await self.rm.client.hset("defense_cache", domain, level.value)
        await self.rm.client.expire("defense_cache", 86400)
        
        return level, compliance_status

    async def _run_probe(self, url: str) -> DefenseLevel:
        """
        Dispara um request nua (Nível 0) e observa a resposta para detectar WAFs.
        """
        logger.info(f"Disparando sonda de reconhecimento (Probe) para {url}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    headers = response.headers
                    text = await response.text()
                    status = response.status
                    cookies = " ".join([c.key for c in session.cookie_jar])
                    
                    signals = {
                        "cf_ray": "cf-ray" in headers or "cf-mitigated" in headers,
                        "js_challenge": "Just a moment" in text or "cloudflare" in text.lower(),
                        "datadome": "datadome" in cookies.lower(),
                        "perimeterx": "__px" in cookies.lower(),
                        "akamai": "ak_bmsc" in cookies.lower(),
                        "captcha": "captcha" in text.lower(),
                        "status": status,
                    }
                    
                    return self._route_signals(signals)
                    
        except asyncio.TimeoutError:
            # Timeout geralmente é block severo ou host morto
            return DefenseLevel.LEVEL_2 
        except Exception as e:
            logger.warning(f"Sonda falhou para {url}: {e}. Assumindo NIVEL 1 por segurança.")
            return DefenseLevel.LEVEL_1

    def _route_signals(self, signals: Dict[str, Any]) -> DefenseLevel:
        if signals["perimeterx"] or signals["akamai"] or (signals["status"] == 403 and signals["captcha"]):
            return DefenseLevel.LEVEL_4
        if signals["datadome"]:
            return DefenseLevel.LEVEL_3
        if signals["js_challenge"] or signals["status"] in (403, 401):
            return DefenseLevel.LEVEL_2
        if signals["cf_ray"]:
            return DefenseLevel.LEVEL_1
            
        return DefenseLevel.LEVEL_0 # Zona Livre
