# ==============================================
# LARIZINHA STORE - DECORATORS UTILITÁRIOS
# ==============================================

import time
import logging
from functools import wraps
from typing import Callable, Any

from config import ADMIN_IDS, FLOOD_MAX_MESSAGES_PER_MINUTE, FLOOD_BLOCK_SECONDS

logger = logging.getLogger(__name__)

# Cache simples para controle de flood (em produção, usar Redis)
_flood_cache: dict[int, list[float]] = {}


def admin_only(func: Callable) -> Callable:
    """
    Decorator que permite a execução do handler apenas para administradores.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Tenta obter o ID do usuário a partir dos argumentos
        user_id = None
        for arg in args:
            if hasattr(arg, "from_user") and arg.from_user:
                user_id = arg.from_user.id
                break
        if not user_id:
            # Tenta obter de callback_query
            for arg in args:
                if hasattr(arg, "message") and arg.message and arg.message.from_user:
                    user_id = arg.message.from_user.id
                    break

        if user_id not in ADMIN_IDS:
            logger.warning(f"Acesso negado para user_id={user_id}")
            # Se houver mensagem ou callback, responde
            for arg in args:
                if hasattr(arg, "answer"):
                    await arg.answer("⛔ Acesso negado.", show_alert=True)
                elif hasattr(arg, "reply"):
                    await arg.reply("⛔ Acesso negado.")
            return None
        return await func(*args, **kwargs)
    return wrapper


def flood_control(func: Callable) -> Callable:
    """
    Decorator que limita a quantidade de mensagens por minuto por usuário.
    Se exceder, bloqueia temporariamente.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Obtém user_id
        user_id = None
        for arg in args:
            if hasattr(arg, "from_user") and arg.from_user:
                user_id = arg.from_user.id
                break
        if not user_id:
            for arg in args:
                if hasattr(arg, "message") and arg.message and arg.message.from_user:
                    user_id = arg.message.from_user.id
                    break

        if user_id is not None:
            now = time.time()
            timestamps = _flood_cache.get(user_id, [])
            # Remove registros antigos
            timestamps = [t for t in timestamps if now - t < 60]
            if len(timestamps) >= FLOOD_MAX_MESSAGES_PER_MINUTE:
                logger.warning(f"Flood detectado para user_id={user_id}")
                for arg in args:
                    if hasattr(arg, "answer"):
                        await arg.answer(
                            f"⚠️ Você está enviando mensagens muito rápido. Aguarde {FLOOD_BLOCK_SECONDS} segundos.",
                            show_alert=True
                        )
                    elif hasattr(arg, "reply"):
                        await arg.reply(
                            f"⚠️ Você está enviando mensagens muito rápido. Aguarde {FLOOD_BLOCK_SECONDS} segundos."
                        )
                return None
            timestamps.append(now)
            _flood_cache[user_id] = timestamps

        return await func(*args, **kwargs)
    return wrapper
