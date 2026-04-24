import asyncio
import random
import time
from typing import Optional, Dict
import logging
import aiohttp
from redis.asyncio import Redis

logger = logging.getLogger("ProxyIntelligence")

# ==========================================
# 1. Motor de Rotação Dual com Anti-Thundering Herd
# ==========================================
class ProxyRotationEngine:
    """
    Gerencia a auto-rotação configurada no painel e a rotação forçada (on-demand) via API.
    Aplica o Jitter para evitar que o "Thundering Herd" (manada) derrube o site ou a API de rotação.
    """
    def __init__(self, api_url: str, port_id: str, api_key: str):
        self.api_url = api_url
        self.port_id = port_id
        self.api_key = api_key
        self.min_rotation_interval = 10  # segundos (evita spam na API)
        self._last_rotation = 0.0
        # Lock assíncrono garante que apenas 1 worker por porta ative a rotação ao mesmo tempo
        self._rotation_lock = asyncio.Lock()

    async def rotate_on_block(self, status_code: int):
        if status_code in [403, 503, 401]: # Banimento ou JS Challenge Falho
            async with self._rotation_lock:
                now = time.time()
                if now - self._last_rotation < self.min_rotation_interval:
                    # Já rotacionou há pouco tempo, apenas aguarda a poeira baixar
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    return

                # Jitter Tático: espalha a chamada de rotação
                jitter = random.uniform(0.5, 3.0)
                await asyncio.sleep(jitter)

                logger.warning(f"[Rotator] WAF Detectado ({status_code}). Forçando Rotação de IP na porta {self.port_id} via Proxies.sx...")

                # Chamada de API real para Proxies.sx
                api_endpoint = f"https://client.proxies.sx/api/ports/{self.port_id}/rotate"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            api_endpoint,
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=10
                        ) as response:
                            response.raise_for_status()
                            logger.info(f"[Rotator] IP rotacionado com sucesso na operadora para a porta {self.port_id}!")
                except Exception as e:
                    logger.error(f"[Rotator] Falha ao rotacionar na Proxies.sx para a porta {self.port_id}: {e}")

                self._last_rotation = time.time()
                await asyncio.sleep(3)  # Tempo físico para o IP propagar na rede da operadora

        elif status_code == 429: # Rate Limit
            # Adiciona Jitter ao Retry-After para que as retentativas não batam juntas
            retry_after = 30 + random.uniform(0.0, 15.0)
            logger.warning(f"[Rotator] Rate Limit (429). Congelando porta {self.port_id} por {retry_after:.1f}s.")
            await asyncio.sleep(retry_after)

# ==========================================
# 2. Rastreador de Sucesso por Domínio (Memória Institucional)
# ==========================================
class SuccessRateTracker:
    """
    Grava e consulta no Redis a taxa de sucesso histórica de um domínio para cada Tier de Proxy.
    Evita o teste "cego" e pula direto para o Tier que funciona.
    """
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def record_attempt(self, domain: str, tier: int, success: bool):
        """Atualiza os contadores de sucesso e falha no Redis Hash."""
        # Estrutura do Hash: domain:stats -> { "tier0_success": 10, "tier0_fail": 2, ... }
        field_base = f"tier{tier}"
        field_action = "success" if success else "fail"
        field_name = f"{field_base}_{field_action}"

        # Pipeline para atomicidade
        pipe = self.redis.pipeline()
        pipe.hincrby(f"domain_stats:{domain}", field_name, 1)
        # Mantém histórico vivo por 7 dias (adapta-se a mudanças no WAF)
        pipe.expire(f"domain_stats:{domain}", 604800)
        await pipe.execute()

    async def get_best_tier(self, domain: str, min_success_rate: float = 0.70) -> Optional[int]:
        """Analisa o histórico e retorna o menor Tier que mantém a taxa de sucesso mínima."""
        stats = await self.redis.hgetall(f"domain_stats:{domain}")
        if not stats:
            return None # Sem histórico, segue o fluxo normal (0 -> 1 -> ...)

        for tier in range(6): # Tiers de 0 a 5
            successes = int(stats.get(f"tier{tier}_success", 0))
            fails = int(stats.get(f"tier{tier}_fail", 0))
            total = successes + fails

            # Só confia na taxa se tiver pelo menos 5 tentativas documentadas
            if total >= 5:
                rate = successes / total
                if rate >= min_success_rate:
                    return tier
        return None

# ==========================================
# 3. O Gerenciador Inteligente (O Maestro)
# ==========================================
class ProxyIntelligenceManager:
    """
    O cérebro que decide qual proxy usar, consultando o histórico e a classificação do WAF.
    """
    def __init__(self, tracker: SuccessRateTracker, rotator_api: str, api_key: str):
        self.tracker = tracker
        self.api_key = api_key
        # Pool de rotatores (1 por porta configurada no painel)
        # Exemplo: port_id como string/id esperado pela API
        self.rotators: Dict[str, ProxyRotationEngine] = {
             "port_8001": ProxyRotationEngine(rotator_api, "8001", api_key),
             "port_8002": ProxyRotationEngine(rotator_api, "8002", api_key),
        }

    def get_proxy_string_for_tier(self, tier: int) -> Optional[str]:
         # Lógica de roteamento real: mapear tiers para as portas/credenciais do provedor
         # PLACEHOLDERS PRONTOS PARA SUBSTITUIÇÃO FÁCIL:
         if tier in [0, 1, 2]: return None # Sem proxy comercial (usa Datacenter/IP Limpo local)
         if tier in [3, 4]: return "http://DUMMY_MOBILE_USER:DUMMY_MOBILE_PASS@mobile.proxies.sx:8001" # Mobile 4G/5G
         if tier == 5: return "http://DUMMY_RES_USER:DUMMY_RES_PASS@res.iproyal.com:9001" # Residencial Fortress

    async def resolve_tier_for_domain(self, domain: str, current_defense_level: int) -> int:
        """
        Calcula o Tier. O Histórico de sucesso sobrepõe a classificação nua do WAF.
        Se o WAF for nível 1, mas o histórico diz que só funciona no Mobile (Tier 3), ele pula pro 3.
        """
        historical_best = await self.tracker.get_best_tier(domain)

        if historical_best is not None:
             # O sistema aprendeu: escolhe o que for mais agressivo entre o WAF detectado e o histórico
             return max(historical_best, current_defense_level)

        return current_defense_level

    def get_rotator_for_tier(self, tier: int) -> Optional[ProxyRotationEngine]:
        # Para Tiers móveis/residenciais, retorna o motor para aplicar Jitter em caso de falha
        if tier >= 3:
             # Em produção, você faria um rodízio (Round-Robin) entre as portas disponíveis
             return self.rotators["port_8001"]
        return None
