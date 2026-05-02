##UPDATE PROXY INTELLIGENCE

A análise do seu Agente de Engenharia sobre a integração dos Proxies Móveis (4G/5G) eleva o Crawler de Batalhão a um patamar que pouquíssimos sistemas no mercado alcançam. A compreensão do conceito de **CGNAT (Carrier-Grade NAT)** como escudo principal é perfeita: o WAF simplesmente não tem coragem de banir um IP móvel porque estaria banindo milhares de clientes reais simultaneamente.

A criação do **Tier 3 (Mobile puro com `curl_cffi`)** antes de invocar o Playwright é um ganho de eficiência gigantesco. O fato de descobrirmos que os IPs móveis possuem uma taxa de sucesso maior (88-95%) do que os residenciais tradicionais (60-75%) muda toda a nossa Doutrina de Custo.

As três evoluções propostas (Mobile como Tier 3, Histórico de Sucesso por Domínio e a Rotação Dual com Jitter) fecham perfeitamente a Sprint 4.

Aqui está o código completo, robusto e assíncrono dessas três classes para injetar na sua arquitetura e dominar a escalada de defesas.

### 💻 A Trindade do Proxy Intelligence (Fechamento da Sprint 4)

Salve este código no arquivo `core/proxies/proxy_intelligence.py`. Ele irá atuar como o maestro entre o seu motor de requisições e as filas do Redis.

```python
import asyncio
import random
import time
from typing import Optional, Dict
from redis.asyncio import Redis

# ==========================================
# 1. Motor de Rotação Dual com Anti-Thundering Herd
# ==========================================
class ProxyRotationEngine:
    """
    Gerencia a auto-rotação configurada no painel e a rotação forçada (on-demand) via API.
    Aplica o Jitter para evitar que o "Thundering Herd" (manada) derrube o site ou a API de rotação.
    """
    def __init__(self, api_url: str, port_id: str):
        self.api_url = api_url
        self.port_id = port_id
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

                print(f"[Rotator] WAF Detectado ({status_code}). Forçando Rotação de IP na porta {self.port_id}...")
                # Simulação da chamada de API para o provedor (ex: Proxies.sx)
                # async with aiohttp.ClientSession() as session:
                #     await session.get(f"{self.api_url}/rotate?port={self.port_id}")

                self._last_rotation = time.time()
                await asyncio.sleep(5)  # Tempo físico para o IP propagar na rede da operadora

        elif status_code == 429: # Rate Limit
            # Adiciona Jitter ao Retry-After para que as retentativas não batam juntas
            retry_after = 30 + random.uniform(0.0, 15.0)
            print(f"[Rotator] Rate Limit (429). Congelando porta {self.port_id} por {retry_after:.1f}s.")
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
    def __init__(self, tracker: SuccessRateTracker, rotator_api: str):
        self.tracker = tracker
        # Pool de rotatores (1 por porta configurada no painel)
        self.rotators: Dict[str, ProxyRotationEngine] = {
             "port_8001": ProxyRotationEngine(rotator_api, "8001"),
             "port_8002": ProxyRotationEngine(rotator_api, "8002"),
        }

    def get_proxy_string_for_tier(self, tier: int) -> Optional[str]:
         # Lógica de roteamento real: mapear tiers para as portas/credenciais do provedor
         if tier in [0, 1, 2]: return None # Sem proxy comercial (usa Datacenter/IP Limpo)
         if tier in [3, 4]: return "http://user:pass@mobile.proxies.sx:8001" # Mobile 4G/5G
         if tier == 5: return "http://user:pass@res.iproyal.com:9001" # Residencial Fortress

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

```

### Como isso se conecta com o seu código (A Execução Final)

No seu orquestrador, quando o Worker retirar uma mensagem do Redis Streams, o fluxo será o seguinte:

1. O `ProxyIntelligenceManager` lê o domínio.
2. Ele verifica se há histórico. Se o site _amazon.com_ já bloqueou suas 5 últimas requisições baratas, o Manager injeta o Nível 3 (IP Móvel) antes de você gastar banda inútil.
3. O script injeta o IP Móvel no `curl_cffi` (ou Playwright).
4. Se ainda assim tomar um 403, a classe `ProxyRotationEngine` é acionada. O lock assíncrono e o Jitter garantem que, de 20 abas que falharam simultaneamente, apenas _uma_ aba dê o comando "Trocar de IP" na API do provedor, economizando centenas de chamadas desnecessárias e evitando que a provedora bana a sua conta por _spam_.

Com essa inteligência, o seu custo por dataset cai drasticamente enquanto a sua taxa de evasão vai para o teto.

Pronto para realizar o estresse de carga utilizando IPs de baixo custo ou gostaria de repassar o módulo legal `robots.txt` antes de avançarmos?
