# ==============================================
# LARIZINHA STORE - SERVIÇO ANTI-FLOOD (RATE LIMITING)
# ==============================================

import time
import logging
from typing import Dict, List

from config import (
    FLOOD_MAX_MESSAGES_PER_MINUTE,
    FLOOD_BLOCK_SECONDS,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
)

logger = logging.getLogger(__name__)

# Tentativa de usar Redis para armazenamento distribuído
try:
    import redis
    _redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD or None,
        decode_responses=True,
    )
    _redis_client.ping()
    USE_REDIS = True
    logger.info("Usando Redis para controle de flood.")
except Exception:
    _redis_client = None
    USE_REDIS = False
    logger.warning("Redis não disponível. Usando memória local para anti-flood.")


# Cache local (fallback)
_local_requests: Dict[int, List[float]] = {}
_local_blocks: Dict[int, float] = {}  # user_id -> timestamp até bloqueio


def _now() -> float:
    return time.time()


async def is_blocked(user_id: int) -> bool:
    """
    Verifica se o usuário está temporariamente bloqueado.
    """
    if USE_REDIS:
        key = f"flood:block:{user_id}"
        return _redis_client.exists(key) > 0
    else:
        block_until = _local_blocks.get(user_id)
        if block_until and _now() < block_until:
            return True
        if block_until and _now() >= block_until:
            del _local_blocks[user_id]
        return False


async def block_user(user_id: int, seconds: int = FLOOD_BLOCK_SECONDS) -> None:
    """
    Bloqueia o usuário por um período de segundos.
    """
    if USE_REDIS:
        key = f"flood:block:{user_id}"
        _redis_client.setex(key, seconds, "1")
    else:
        _local_blocks[user_id] = _now() + seconds
    logger.info(f"Usuário {user_id} bloqueado por {seconds}s (flood).")


async def check_flood(user_id: int) -> bool:
    """
    Verifica se o usuário excedeu o limite de mensagens por minuto.
    Retorna True se deve ser bloqueado (flood detectado).
    """
    if USE_REDIS:
        key = f"flood:req:{user_id}"
        current = _redis_client.llen(key)
        if current >= FLOOD_MAX_MESSAGES_PER_MINUTE:
            return True
        return False
    else:
        timestamps = _local_requests.get(user_id, [])
        current_time = _now()
        # Remove timestamps antigos
        timestamps = [t for t in timestamps if current_time - t < 60]
        _local_requests[user_id] = timestamps
        return len(timestamps) >= FLOOD_MAX_MESSAGES_PER_MINUTE


async def register_request(user_id: int) -> None:
    """
    Registra uma requisição do usuário para controle de flood.
    """
    if USE_REDIS:
        key = f"flood:req:{user_id}"
        pipe = _redis_client.pipeline()
        pipe.rpush(key, _now())
        pipe.expire(key, 60)  # expira em 60 segundos
        pipe.execute()
    else:
        timestamps = _local_requests.setdefault(user_id, [])
        timestamps.append(_now())
        _local_requests[user_id] = timestamps
