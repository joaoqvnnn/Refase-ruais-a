# ==============================================
# LARIZINHA STORE - HANDLER ADMIN PRODUTOS
# ==============================================

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func, update
from database.connection import async_session
from database.models import Produto, Categoria, EstoqueItem, Log
from keyboards.admin import admin_products_menu_keyboard, admin_back_keyboard
from texts.admin import get_admin_message
from utils.decorators import admin_only
from utils.validators import (
    validar_nome_produto,
    validar_preco,
    validar_estoque,
    validar_porcentagem,
)

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# ESTADOS FSM PARA ADICIONAR/EDITAR PRODUTO
# ==============================================
class ProductForm(StatesGroup):
    waiting_nome = State()
    waiting_emoji = State()
    waiting_categoria = State()
    waiting_preco = State()
    waiting_descricao = State()
    waiting_garantia = State()
    waiting_mensagem_entrega = State()
    waiting_confirmacao = State()


class StockForm(StatesGroup):
    waiting_produto = State()
    waiting_conteudo = State()


# ==============================================
# MENU PRINCIPAL DE PRODUTOS
# ==============================================
@router.callback_query(F.data == "admin_products")
@admin_only
async def admin_products_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 Gerenciar Produtos\n\nEscolha uma ação:",
        reply_markup=admin_products_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR PRODUTOS
# ==============================================
@router.callback_query(F.data == "admin_product_list")
@admin_only
async def admin_product_list(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Produto).order_by(Produto.id.desc()).limit(10)
        )
        produtos = result.scalars().all()

    if not produtos:
        texto = "Nenhum produto cadastrado."
    else:
        linhas = []
        for p in produtos:
            linhas.append(
                f"#{p.id} {p.emoji or '🛒'} {p.nome} - R$ {float(p.preco):.2f} (Estoque: {p.estoque})"
            )
        texto = "📋 Produtos (últimos 10):\n\n" + "\n".join(linhas)

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_products")
    )
    await callback.answer()


# ==============================================
# ADICIONAR PRODUTO (FSM)
# ==============================================
@router.callback_query(F.data == "admin_product_add")
@admin_only
async def admin_product_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductForm.waiting_nome)
    await callback.message.answer(
        "Digite o nome do produto:"
    )
    await callback.answer()


@router.message(ProductForm.waiting_nome)
@admin_only
async def product_nome_recebido(message: Message, state: FSMContext):
    nome = message.text.strip()
    if not validar_nome_produto(nome):
        await message.answer("Nome inválido. Deve ter entre 2 e 255 caracteres.")
        return
    await state.update_data(nome=nome)
    await state.set_state(ProductForm.waiting_emoji)
    await message.answer("Digite o emoji do produto (ex: 🎬):")


@router.message(ProductForm.waiting_emoji)
@admin_only
async def product_emoji_recebido(message: Message, state: FSMContext):
    emoji = message.text.strip() or "🛒"
    await state.update_data(emoji=emoji)
    await state.set_state(ProductForm.waiting_categoria)

    # Lista categorias disponíveis
    async with async_session() as session:
        result = await session.execute(select(Categoria).where(Categoria.ativo == True))
        categorias = result.scalars().all()
    if not categorias:
        await message.answer("Nenhuma categoria ativa. Crie uma categoria primeiro.")
        await state.clear()
        return
    texto = "Escolha a categoria (digite o ID):\n\n"
    for c in categorias:
        texto += f"#{c.id} - {c.nome}\n"
    await message.answer(texto)


@router.message(ProductForm.waiting_categoria)
@admin_only
async def product_categoria_recebida(message: Message, state: FSMContext):
    try:
        categoria_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID inválido. Digite um número.")
        return
    async with async_session() as session:
        categoria = await session.get(Categoria, categoria_id)
    if not categoria:
        await message.answer("Categoria não encontrada.")
        return
    await state.update_data(categoria_id=categoria_id)
    await state.set_state(ProductForm.waiting_preco)
    await message.answer("Digite o preço do produto (ex: 6.00):")


@router.message(ProductForm.waiting_preco)
@admin_only
async def product_preco_recebido(message: Message, state: FSMContext):
    try:
        preco = Decimal(message.text.replace(",", "."))
        if preco <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("Preço inválido.")
        return
    await state.update_data(preco=preco)
    await state.set_state(ProductForm.waiting_descricao)
    await message.answer("Digite a descrição do produto (use /pular para deixar vazio):")


@router.message(ProductForm.waiting_descricao)
@admin_only
async def product_descricao_recebida(message: Message, state: FSMContext):
    descricao = message.text.strip()
    if descricao == "/pular":
        descricao = ""
    await state.update_data(descricao=descricao)
    await state.set_state(ProductForm.waiting_garantia)
    await message.answer("Digite a garantia em dias (ex: 30):")


@router.message(ProductForm.waiting_garantia)
@admin_only
async def product_garantia_recebida(message: Message, state: FSMContext):
    try:
        garantia = int(message.text.strip())
        if garantia < 0:
            raise ValueError
    except ValueError:
        await message.answer("Valor inválido.")
        return
    await state.update_data(garantia_dias=garantia)
    await state.set_state(ProductForm.waiting_mensagem_entrega)
    await message.answer(
        "Digite a mensagem de entrega (use variáveis como {email}, {senha}, {link} se necessário). /pular para padrão:"
    )


@router.message(ProductForm.waiting_mensagem_entrega)
@admin_only
async def product_mensagem_entrega_recebida(message: Message, state: FSMContext):
    mensagem = message.text.strip()
    if mensagem == "/pular":
        mensagem = "{conteudo}"
    await state.update_data(mensagem_entrega=mensagem)
    await state.set_state(ProductForm.waiting_confirmacao)

    dados = await state.get_data()
    resumo = (
        "Confirme os dados do produto:\n\n"
        f"Nome: {dados['nome']}\n"
        f"Emoji: {dados['emoji']}\n"
        f"Categoria ID: {dados['categoria_id']}\n"
        f"Preço: R$ {float(dados['preco']):.2f}\n"
        f"Descrição: {dados['descricao'] or 'Sem descrição'}\n"
        f"Garantia: {dados['garantia_dias']} dias\n"
        f"Mensagem de entrega: {dados['mensagem_entrega']}\n\n"
        "Digite /confirmar para salvar ou /cancelar para abortar."
    )
    await message.answer(resumo)


@router.message(ProductForm.waiting_confirmacao)
@admin_only
async def product_confirmacao(message: Message, state: FSMContext):
    if message.text.strip() == "/confirmar":
        dados = await state.get_data()
        async with async_session() as session:
            novo_produto = Produto(
                categoria_id=dados["categoria_id"],
                nome=dados["nome"],
                emoji=dados["emoji"],
                descricao=dados["descricao"],
                preco=dados["preco"],
                estoque=0,
                vendidos=0,
                ativo=True,
                garantia_dias=dados["garantia_dias"],
                mensagem_entrega=dados["mensagem_entrega"],
            )
            session.add(novo_produto)
            await session.commit()
            produto_id = novo_produto.id
            # Log
            log = Log(user_id=message.from_user.id, acao="produto_criado", detalhes={"produto_id": produto_id})
            session.add(log)
            await session.commit()
        await message.answer(f"✅ Produto criado com ID #{produto_id}!")
    else:
        await message.answer("❌ Criação cancelada.")
    await state.clear()


# ==============================================
# ADICIONAR ESTOQUE (FSM)
# ==============================================
@router.callback_query(F.data == "admin_stock_add")
@admin_only
async def admin_stock_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StockForm.waiting_produto)
    await callback.message.answer("Digite o ID do produto para adicionar estoque:")
    await callback.answer()


@router.message(StockForm.waiting_produto)
@admin_only
async def stock_produto_recebido(message: Message, state: FSMContext):
    try:
        produto_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID inválido.")
        return
    async with async_session() as session:
        produto = await session.get(Produto, produto_id)
    if not produto:
        await message.answer("Produto não encontrado.")
        return
    await state.update_data(produto_id=produto_id)
    await state.set_state(StockForm.waiting_conteudo)
    await message.answer(
        f"Produto: {produto.nome}\n\n"
        "Envie o conteúdo do item (ex: email:senha:link) ou um arquivo .txt com um item por linha.\n"
        "Envie /concluir para terminar a adição."
    )


@router.message(StockForm.waiting_conteudo)
@admin_only
async def stock_conteudo_recebido(message: Message, state: FSMContext):
    if message.text and message.text.strip() == "/concluir":
        await state.clear()
        await message.answer("✅ Estoque atualizado!")
        return

    conteudo = message.text.strip() if message.text else ""
    # Se for documento, lê o conteúdo
    if message.document:
        # Baixar e processar arquivo seria implementado aqui
        await message.answer("Processamento de arquivo ainda não implementado.")
        return

    if not conteudo:
        await message.answer("Conteúdo vazio.")
        return

    dados = await state.get_data()
    produto_id = dados["produto_id"]

    async with async_session() as session:
        item = EstoqueItem(produto_id=produto_id, conteudo=conteudo, vendido=False)
        session.add(item)
        # Incrementa estoque do produto
        await session.execute(
            update(Produto).where(Produto.id == produto_id).values(estoque=Produto.estoque + 1)
        )
        await session.commit()

    await message.answer("✅ Item adicionado! Envie outro item ou /concluir.")


# ==============================================
# VER ESTOQUE DE UM PRODUTO (callback separado)
# ==============================================
@router.callback_query(F.data.startswith("admin_stock_view:"))
@admin_only
async def admin_stock_view(callback: CallbackQuery):
    produto_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        produto = await session.get(Produto, produto_id)
        result = await session.execute(
            select(EstoqueItem).where(EstoqueItem.produto_id == produto_id, EstoqueItem.vendido == False).limit(5)
        )
        itens = result.scalars().all()
    if not produto:
        await callback.answer("Produto não encontrado.", show_alert=True)
        return
    texto = f"📦 Estoque de {produto.nome} (disponíveis):\n\n"
    for item in itens:
        texto += f"• {item.conteudo[:50]}...\n"
    texto += f"\nTotal disponível: {produto.estoque}"
    await callback.message.edit_text(texto, reply_markup=admin_back_keyboard("admin_products"))
    await callback.answer()


# ==============================================
# CANCELAR OPERAÇÕES FSM (comandos)
# ==============================================
@router.message(Command("cancelar"))
@admin_only
async def cancelar_operacao(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Operação cancelada.", reply_markup=admin_back_keyboard())
