# ==============================================
# LARIZINHA STORE - HANDLER ADMIN CATEGORIAS
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import Categoria, Produto, Log
from keyboards.admin import admin_categories_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only
from utils.validators import validar_nome_produto

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA ADICIONAR/EDITAR CATEGORIA
# ==============================================
class CategoryForm(StatesGroup):
    waiting_nome = State()
    waiting_emoji = State()
    waiting_ordem = State()


# ==============================================
# MENU PRINCIPAL DE CATEGORIAS
# ==============================================
@router.callback_query(F.data == "admin_categories")
@admin_only
async def admin_categories_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📁 Gerenciar Categorias\n\nEscolha uma ação:",
        reply_markup=admin_categories_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR CATEGORIAS
# ==============================================
@router.callback_query(F.data == "admin_category_list")
@admin_only
async def admin_category_list(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Categoria).order_by(Categoria.ordem)
        )
        categorias = result.scalars().all()

    if not categorias:
        texto = "Nenhuma categoria cadastrada."
        teclado = admin_categories_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for c in categorias:
            linhas.append(f"#{c.id} {c.emoji or '📁'} {c.nome} (ordem: {c.ordem})")
            botoes.append([
                InlineKeyboardButton(text=f"✏️ {c.nome}", callback_data=f"admin_category_edit:{c.id}"),
                InlineKeyboardButton(text=f"🗑️", callback_data=f"admin_category_delete:{c.id}"),
            ])
        texto = "📋 Categorias:\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_categories")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# INICIAR ADIÇÃO OU EDIÇÃO DE CATEGORIA
# ==============================================
@router.callback_query(F.data == "admin_category_add")
@admin_only
async def admin_category_add_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(CategoryForm.waiting_nome)
    await callback.message.answer("Digite o nome da categoria:")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_category_edit:"))
@admin_only
async def admin_category_edit(callback: CallbackQuery, state: FSMContext):
    categoria_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        categoria = await session.get(Categoria, categoria_id)
    if not categoria:
        await callback.answer("Categoria não encontrada.", show_alert=True)
        return

    await state.update_data(
        categoria_id=categoria_id,
        nome_original=categoria.nome,
        emoji_original=categoria.emoji,
        ordem_original=categoria.ordem
    )
    await state.set_state(CategoryForm.waiting_nome)
    await callback.message.answer(
        f"Editar categoria #{categoria_id}\n\n"
        f"Nome atual: {categoria.nome}\n"
        "Digite o novo nome (ou /manter para manter):"
    )
    await callback.answer()


# ==============================================
# HANDLERS FSM (com suporte a criação e edição)
# ==============================================
@router.message(CategoryForm.waiting_nome)
@admin_only
async def category_nome(message: Message, state: FSMContext):
    dados = await state.get_data()
    editando = "categoria_id" in dados
    nome = message.text.strip()
    if nome == "/manter" and editando:
        nome = dados.get("nome_original")
    if not validar_nome_produto(nome):
        await message.answer("Nome inválido. Use entre 2 e 255 caracteres.")
        return
    await state.update_data(nome=nome)
    await state.set_state(CategoryForm.waiting_emoji)
    await message.answer("Digite o emoji (ex: 🎬) ou /manter para manter atual ou /pular para 📁:")


@router.message(CategoryForm.waiting_emoji)
@admin_only
async def category_emoji(message: Message, state: FSMContext):
    dados = await state.get_data()
    editando = "categoria_id" in dados
    emoji = message.text.strip()
    if emoji == "/manter" and editando:
        emoji = dados.get("emoji_original")
    elif emoji == "/pular" or not emoji:
        emoji = "📁"
    await state.update_data(emoji=emoji)
    await state.set_state(CategoryForm.waiting_ordem)
    await message.answer("Digite a ordem de exibição (número) ou /manter para manter:")


@router.message(CategoryForm.waiting_ordem)
@admin_only
async def category_ordem(message: Message, state: FSMContext):
    dados = await state.get_data()
    editando = "categoria_id" in dados
    ordem_str = message.text.strip()
    if ordem_str == "/manter" and editando:
        ordem = dados.get("ordem_original")
    else:
        try:
            ordem = int(ordem_str)
            if ordem < 0:
                raise ValueError
        except ValueError:
            await message.answer("Ordem inválida. Digite um número inteiro não negativo.")
            return

    async with async_session() as session:
        if editando:
            categoria = await session.get(Categoria, dados["categoria_id"])
            if categoria:
                categoria.nome = dados["nome"]
                categoria.emoji = dados["emoji"]
                categoria.ordem = ordem
                await session.commit()
                await message.answer("✅ Categoria atualizada!")
            else:
                await message.answer("Categoria não encontrada.")
        else:
            nova = Categoria(nome=dados["nome"], emoji=dados["emoji"], ordem=ordem, ativo=True)
            session.add(nova)
            await session.commit()
            await message.answer(f"✅ Categoria criada com ID #{nova.id}!")
            # Log
            log = Log(user_id=message.from_user.id, acao="categoria_criada", detalhes={"categoria_id": nova.id})
            session.add(log)
            await session.commit()

    await state.clear()


# ==============================================
# REMOVER CATEGORIA
# ==============================================
@router.callback_query(F.data.startswith("admin_category_delete:"))
@admin_only
async def admin_category_delete(callback: CallbackQuery):
    categoria_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        categoria = await session.get(Categoria, categoria_id)
        if not categoria:
            await callback.answer("Categoria não encontrada.", show_alert=True)
            return
        # Verifica produtos vinculados
        result = await session.execute(select(func.count(Produto.id)).where(Produto.categoria_id == categoria_id))
        total_produtos = result.scalar() or 0
        if total_produtos > 0:
            await callback.answer(
                f"Não é possível excluir: existem {total_produtos} produto(s) vinculado(s).",
                show_alert=True,
            )
            return
        await session.delete(categoria)
        await session.commit()
        # Log
        log = Log(user_id=callback.from_user.id, acao="categoria_removida", detalhes={"categoria_id": categoria_id})
        session.add(log)
        await session.commit()

    await callback.message.edit_text(
        "✅ Categoria removida.",
        reply_markup=admin_categories_menu_keyboard()
    )
    await callback.answer()
