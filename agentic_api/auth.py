import time
from fastapi import HTTPException, Security, Response
from fastapi.security.api_key import APIKeyHeader
from core.mq.redis_manager import RedisManager

# O header onde a chave deve ser enviada
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

# Instância compartilhada para gerenciar os rate limits
rm = RedisManager(tenant_db_index=0)

# Limite estrito: 60 requests por minuto
RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_WINDOW_MS = 60000

async def validate_api_key_and_rate_limit(
    response: Response,
    api_key: str = Security(API_KEY_HEADER)
) -> str:
    """
    1. Valida a Chave de API via Redis Hash. (HTTP 401 se falso ou revogado)
    2. Valida o limite comercial (HTTP 402 se quota estourada)
    3. Realiza débito atômico na quota.
    4. Aplica Rate Limiting Anti-Spam (HTTP 429).
    """
    redis_key = f"auth:key:{api_key}"
    
    # 1. Validação de Existência e Status no Cofre
    key_data = await rm.client.hgetall(redis_key)
    
    if not key_data:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Invalid API Key. Access Denied."
        )
        
    status = key_data.get("status")
    if status != "active":
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: API Key is revoked or inactive."
        )
        
    # 2. Validação Comercial (A Catraca)
    quota_limit = int(key_data.get("quota_limit", 0))
    quota_used = int(key_data.get("quota_used", 0))
    client_name = key_data.get("client_name", "Unknown")
    
    if quota_used >= quota_limit:
        raise HTTPException(
            status_code=402, 
            detail="Limites do Trial NeuralSafety atingidos. Entre em contato diretamente com nosso CEO para liberação e upgrade para a licença Enterprise."
        )
        
    # 3. Débito Atômico
    new_quota_used = await rm.client.hincrby(redis_key, "quota_used", 1)
    
    # Adicionando o header de Remaining
    remaining = max(0, quota_limit - new_quota_used)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    # 4. Rate Limiting (Sliding Window Algorithm Atômico) contra SPAM
    import uuid
    current_time = int(time.time() * 1000)
    window_start = current_time - RATE_LIMIT_WINDOW_MS
    
    ratelimit_key = f"ratelimit:{client_name}"
    unique_member = f"{current_time}:{uuid.uuid4()}"
    
    try:
        pipeline = rm.client.pipeline(transaction=True)
        pipeline.zremrangebyscore(ratelimit_key, 0, window_start)
        pipeline.zadd(ratelimit_key, {unique_member: current_time})
        pipeline.zcard(ratelimit_key)
        pipeline.expire(ratelimit_key, 60)
        
        results = await pipeline.execute()
        request_count = results[2]
        
        if request_count > RATE_LIMIT_MAX_REQUESTS:
            # Reverte o débito comercial se bateu no limite de spam
            await rm.client.hincrby(redis_key, "quota_used", -1)
            raise HTTPException(
                status_code=429, 
                detail=f"Too Many Requests: Enterprise spam limit is {RATE_LIMIT_MAX_REQUESTS} requests per minute."
            )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"⚠️ Redis Rate Limiter Offline: {e}. Permitindo requisição em modo degradado.")
        
    return client_name

