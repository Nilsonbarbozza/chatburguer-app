import asyncio
import os
import sys
# Adiciona a raiz do projeto ao path para localizar o 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from core.utils import setup_logging
from core.mq.redis_manager import RedisManager
from core.defense.intelligence import DefenseIntelligence, DefenseLevel

setup_logging()
logger = logging.getLogger("ArsenalTeste")

# Substituimos temporariamente a porta pra localhost pra rodar direto do Terminal Windows (fora do Docker)
os.environ["REDIS_URL"] = "redis://localhost:6379"

ALVOS_TESTE = [
    # Exemplo 1: Respeito padrão (Good Bot)
    {"url": "https://example.com/", "respect_robots": "true"},  

    # Exemplo 2: Alvo Protegido com Respeito
    {"url": "https://blog.dsacademy.com.br/firecrawl-e-web-scraping-inteligente-com-ia/", "respect_robots": "true"},

    # Exemplo 3: Forçando ignorar Robots (Decisão do Cliente)
    {"url": "https://www.google.com/search?q=scraping", "respect_robots": "false"},
]

async def fire_test():
    logger.info("🚀 Prenchimento de Payload de Teste na Fila de Ingestão...")
    rm = RedisManager(tenant_db_index=0)

    for alvo in ALVOS_TESTE:
        try:
            # Agora jogamos tudo na boca do funil (Intelligence)
            await rm.client.xadd("stream:ingestion", alvo)
            logger.info(f" ╰-> Injetado na Fila stream:ingestion | URL: {alvo['url']}")
        except Exception as e:
             logger.error(f"Erro na URL {alvo['url']}: {e}")

    await rm.close()
    logger.info("✅ Fogo Lançado! O Sonar de Inteligência processará a triagem agora.")

if __name__ == "__main__":
    asyncio.run(fire_test())
