# ==============================================
# LARIZINHA STORE - HANDLER CATÁLOGO
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from sqlalchemy import select
from database.connection import async_session
from database.models import User, Categoria, Produto
from keyboards.client import catalog_keyboard, products_keyboard, back_to_main_keyboard
from texts.client import get_message
from config import BOT_USERNAME

logger = logging.getLogger(__name__)
router = Router()


async def show_categories(callback: CallbackQuery) -> None:
    """
    Exibe a lista de categorias disponíveis.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

        # Busca categorias ativas ordenadas por ordem
        result = await session.execute(
            select(Categoria).where(Categoria.ativo == True).order_by(Categoria.ordem)
        )
        categorias = result.scalars().all()

    if not categorias:
        texto = "📱 Nenhuma categoria disponível no momento."
        await callback.message.edit_text(texto, reply_markup=back_to_main_keyboard())
        await callback.answer()
        return

    # Monta lista de dicionários para o teclado
    cats = [{"id": c.id, "nome": c.nome, "emoji": c.emoji or "📁"} for c in categorias]

    texto = get_message("catalogo", saldo=f"{saldo:.2f}", NOME_BOT=BOT_USERNAME)
    await callback.message.edit_text(texto, reply_markup=catalog_keyboard(cats))
    await callback.answer()


async def show_products_by_category(callback: CallbackQuery, categoria_id: int) -> None:
    """
    Exibe a lista de produtos de uma categoria.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

        categoria = await session.get(Categoria, categoria_id)
        categoria_nome = categoria.nome if categoria else "Categoria"

        result = await session.execute(
            select(Produto).where(
                Produto.categoria_id == categoria_id,
                Produto.ativo == True
            ).order_by(Produto.nome)
        )
        produtos = result.scalars().all()

    if not produtos:
        texto = "📱 Nenhum produto disponível nesta categoria."
        await callback.message.edit_text(texto, reply_markup=back_to_main_keyboard())
        await callback.answer()
        return

    prods = [{"id": p.id, "nome": p.nome, "emoji": p.emoji or "🛒", "preco": float(p.preco)} for p in produtos]

    texto = get_message(
        "categoria_produtos",
        categoria_nome=categoria_nome,
        saldo=f"{saldo:.2f}",
        NOME_BOT=BOT_USERNAME,
    )
    await callback.message.edit_text(texto, reply_markup=products_keyboard(prods, categoria_id))
    await callback.answer()


# Registro de callbacks
@router.callback_query(F.data == "menu_catalog")
async def menu_catalog(callback: CallbackQuery):
    await show_categories(callback)


@router.callback_query(F.data.startswith("categoria:"))
async def categoria_selecionada(callback: CallbackQuery):
    try:
        categoria_id = int(callback.data.split(":")[1])
        await show_products_by_category(callback, categoria_id)
    except (IndexError, ValueError):
        await callback.answer("Categoria inválida.", show_alert=True)
        await show_categories(callback)


@router.callback_query(F.data == "categoria_voltar")
async def categoria_voltar(callback: CallbackQuery):
    await show_categories(callback)
