# ==============================================
# LARIZINHA STORE - HANDLER DETALHES DO PRODUTO
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from sqlalchemy import select
from database.connection import async_session
from database.models import User, Produto
from keyboards.client import product_details_keyboard, back_to_main_keyboard
from texts.client import get_message
from config import BOT_USERNAME

logger = logging.getLogger(__name__)
router = Router()


# Cache simples para contagem de visualizações (pode ser movido para Redis)
_visualizacoes_cache: dict[int, int] = {}


def registrar_visualizacao(produto_id: int) -> int:
    """
    Incrementa e retorna o número de visualizações de um produto.
    Em produção, isso deve ser armazenado em banco ou Redis.
    """
    atual = _visualizacoes_cache.get(produto_id, 0)
    _visualizacoes_cache[produto_id] = atual + 1
    return atual + 1


async def show_product(callback: CallbackQuery, produto_id: int) -> None:
    """
    Exibe os detalhes do produto selecionado.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

        produto = await session.get(Produto, produto_id)
        if not produto or not produto.ativo:
            texto = "❌ Produto não encontrado ou indisponível."
            await callback.message.edit_text(texto, reply_markup=back_to_main_keyboard())
            await callback.answer()
            return

        estoque = produto.estoque
        vendidos = produto.vendidos
        visualizacoes = registrar_visualizacao(produto_id)

        texto = get_message(
            "produto_detalhes",
            nome_produto=produto.nome,
            preco=f"{float(produto.preco):.2f}",
            saldo=f"{saldo:.2f}",
            estoque=estoque,
            descricao=produto.descricao or "Sem descrição.",
            vendidos=vendidos,
            visualizacoes=visualizacoes,
            garantia_dias=produto.garantia_dias,
        )

        await callback.message.edit_text(
            texto,
            reply_markup=product_details_keyboard(produto_id, saldo_suficiente=(saldo >= float(produto.preco)))
        )
        await callback.answer()


@router.callback_query(F.data.startswith("produto:"))
async def produto_selecionado(callback: CallbackQuery):
    """
    Callback quando um produto é clicado na lista.
    """
    try:
        produto_id = int(callback.data.split(":")[1])
        await show_product(callback, produto_id)
    except (IndexError, ValueError):
        await callback.answer("Produto inválido.", show_alert=True)
        from handlers.client.catalog import show_categories
        await show_categories(callback)


@router.callback_query(F.data == "back_to_catalog")
async def voltar_catalogo(callback: CallbackQuery):
    """
    Volta para a lista de categorias (ou produtos, dependendo do contexto).
    """
    # Por simplicidade, voltamos para as categorias
    from handlers.client.catalog import show_categories
    await show_categories(callback)
