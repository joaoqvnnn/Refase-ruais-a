# ==============================================
# LARIZINHA STORE - SERVIÇO DE ALERTAS DE ESTOQUE
# ==============================================

import logging
from sqlalchemy import select

from database.connection import async_session
from database.models import Alerta, Produto
from aiogram import Bot

logger = logging.getLogger(__name__)


async def notify_product_restock(produto_id: int, bot: Bot) -> int:
    """
    Notifica usuários com alerta ativo para o produto que voltou ao estoque.
    Retorna o número de usuários notificados.
    """
    async with async_session() as session:
        produto = await session.get(Produto, produto_id)
        if not produto or produto.estoque <= 0:
            return 0

        # Busca alertas ativos para o produto
        result = await session.execute(
            select(Alerta).where(
                Alerta.produto_id == produto_id,
                Alerta.ativo == True
            )
        )
        alertas = result.scalars().all()

        enviados = 0
        for alerta in alertas:
            try:
                await bot.send_message(
                    chat_id=alerta.user_id,
                    text=(
                        "🔔 ALERTA DE ESTOQUE\n\n"
                        f"🔥 {produto.nome} voltou ao estoque!\n"
                        f"📦 Disponível: {produto.estoque} unidades."
                    )
                )
                enviados += 1
            except Exception as e:
                logger.error(f"Falha ao enviar alerta para {alerta.user_id}: {e}")

        return enviados


async def send_stock_alerts(bot: Bot) -> None:
    """
    Tarefa periódica (Celery) que pode ser usada para verificar e enviar alertas.
    A notificação principal ocorre no momento do reabastecimento via `notify_product_restock`.
    """
    logger.info("Executando send_stock_alerts (placeholder).")
    # Implementação adicional pode ser feita se necessário.
