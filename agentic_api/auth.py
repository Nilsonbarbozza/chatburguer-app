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

async def atomic_debit(api_key: str, cost: int) -> int:
    """
    Tenta debitar o custo especificado. 
    Retorna o saldo remanescente.
    Se a cota estourar, lança HTTP 402.
    """
    redis_key = f"auth:key:{api_key}"
    lua_script = """
    local limit = tonumber(redis.call('HGET', KEYS[1], 'quota_limit') or '0')
    local used = tonumber(redis.call('HGET', KEYS[1], 'quota_used') or '0')
    local cost = tonumber(ARGV[1])
    
    if (used + cost) > limit then
        return -1
    else
        redis.call('HINCRBY', KEYS[1], 'quota_used', cost)
        return limit - (used + cost)
    end
    """
    remaining = await rm.client.eval(lua_script, 1, redis_key, cost)
    
    if remaining == -1:
        raise HTTPException(
            status_code=402, 
            detail="Limites do Trial NeuralSafety atingidos. Entre em contato diretamente com nosso CEO para liberação e upgrade para a licença Enterprise."
        )
    return remaining

async def refund_credits(api_key: str, cost: int):
    """
    Devolve os créditos em caso de falha do nosso sistema (Timeout/Erro).
    """
    redis_key = f"auth:key:{api_key}"
    await rm.client.hincrby(redis_key, "quota_used", -cost)

async def validate_api_key_and_rate_limit(
    response: Response,
    api_key: str = Security(API_KEY_HEADER)
) -> dict:
    """
    1. Valida a Chave de API via Redis Hash. (HTTP 401 se falso ou revogado)
    2. Aplica Rate Limiting Anti-Spam (HTTP 429).
    Retorna um dicionário com os dados do cliente para que a rota aplique o faturamento dinâmico.
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
        
    # 2. Verificação básica se não está estourado
    quota_limit = int(key_data.get("quota_limit", 0))
    quota_used = int(key_data.get("quota_used", 0))
    client_name = key_data.get("client_name", "Unknown")
    
    if quota_used >= quota_limit:
        raise HTTPException(
            status_code=402, 
            detail="Limites do Trial NeuralSafety atingidos. Entre em contato diretamente com nosso CEO para liberação e upgrade para a licença Enterprise."
        )
    
    # 3. Rate Limiting (Sliding Window Algorithm Atômico) contra SPAM
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
            raise HTTPException(
                status_code=429, 
                detail=f"Too Many Requests: Enterprise spam limit is {RATE_LIMIT_MAX_REQUESTS} requests per minute."
            )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"⚠️ Redis Rate Limiter Offline: {e}. Permitindo requisição em modo degradado.")
        
    return {"api_key": api_key, "client_name": client_name}

