import time
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from core.mq.redis_manager import RedisManager

# O header onde a chave deve ser enviada
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

# Instância compartilhada para gerenciar os rate limits
rm = RedisManager(tenant_db_index=0)

# Simulação de um banco de dados de chaves de clientes (PostgreSQL no futuro)
VALID_API_KEYS = {
    "sk-neuralsafety-enterprise-v1": "customer-001-dev"
}

# Limite estrito: 60 requests por minuto
RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_WINDOW_MS = 60000

async def validate_api_key_and_rate_limit(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    1. Valida a Chave de API. (HTTP 401 se falso)
    2. Aplica o Rate Limit usando Sliding Window no Redis. (HTTP 429 se estourado)
    Retorna o ID do cliente se tudo estiver OK.
    """
    # 1. Validação de Escudo
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Invalid API Key. Access Denied."
        )
        
    customer_id = VALID_API_KEYS[api_key]
    
    # 2. Rate Limiting (Sliding Window Algorithm Atômico)
    import uuid
    current_time = int(time.time() * 1000)
    window_start = current_time - RATE_LIMIT_WINDOW_MS
    
    redis_key = f"ratelimit:{customer_id}"
    unique_member = f"{current_time}:{uuid.uuid4()}"
    
    try:
        # Pipeline transacional atômico
        pipeline = rm.client.pipeline(transaction=True)
        
        # 1. Limpa as requisições antigas
        pipeline.zremrangebyscore(redis_key, 0, window_start)
        # 2. Adiciona a requisição atual com UUID
        pipeline.zadd(redis_key, {unique_member: current_time})
        # 3. Conta quantas restam
        pipeline.zcard(redis_key)
        # 4. Renova a expiração
        pipeline.expire(redis_key, 60)
        
        results = await pipeline.execute()
        request_count = results[2]
        
        if request_count > RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429, 
                detail=f"Too Many Requests: Enterprise limit is {RATE_LIMIT_MAX_REQUESTS} requests per minute."
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fallback: Se o Redis falhar, permitimos a requisição mas logamos o erro.
        import logging
        logging.error(f"⚠️ Redis Rate Limiter Offline: {e}. Permitindo requisição em modo degradado.")
        
    return customer_id

