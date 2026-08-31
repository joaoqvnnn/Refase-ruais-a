# ==============================================
# LARIZINHA STORE - HANDLER FLUXO DE COMPRA
# ==============================================

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sqlalchemy import select, update
from database.connection import async_session
from database.models import User, Produto, Venda, EstoqueItem, Log
from keyboards.client import (
    insufficient_balance_keyboard,
    back_to_main_keyboard,
    payment_waiting_keyboard,
)
from texts.client import get_message
from utils.helpers import format_money, calcular_vencimento, generate_uuid
from config import BOT_USERNAME, PIX_EXPIRATION_MINUTES

logger = logging.getLogger(__name__)
router = Router()


class PurchaseStates(StatesGroup):
    waiting_quantity = State()


async def _obter_usuario(session, user_id):
    return await session.get(User, user_id)


async def _obter_produto(session, produto_id):
    return await session.get(Produto, produto_id)


async def _criar_venda(session, user_id, produto, quantidade, valor_total, forma_pagamento, itens_entregues=None):
    """Cria uma venda e retorna o objeto venda."""
    venda = Venda(
        id=generate_uuid(),
        user_id=user_id,
        produto_id=produto.id,
        quantidade=quantidade,
        valor_total=valor_total,
        data_compra=datetime.now(),
        vencimento=calcular_vencimento(produto.garantia_dias),
        forma_pagamento=forma_pagamento,
        status="pago",
        itens_entregues=itens_entregues or [],
        observacao=None,
    )
    session.add(venda)
    await session.flush()
    return venda


async def _selecionar_itens_estoque(session, produto_id, quantidade):
    """Seleciona N itens não vendidos do estoque de um produto."""
    result = await session.execute(
        select(EstoqueItem)
        .where(EstoqueItem.produto_id == produto_id, EstoqueItem.vendido == False)
        .limit(quantidade)
    )
    itens = result.scalars().all()
    if len(itens) < quantidade:
        return None
    conteudos = []
    for item in itens:
        item.vendido = True
        conteudos.append(item.conteudo)
    return conteudos


async def _entregar_produto(callback: CallbackQuery, user_id, venda, produto, conteudos):
    """Monta mensagem de entrega e envia ao usuário."""
    conteudo_str = "\n\n".join(conteudos)
    texto = get_message(
        "compra_aprovada",
        produto=produto.nome,
        valor=f"{float(venda.valor_total):.2f}",
        data=venda.data_compra.strftime("%d/%m/%Y"),
        hora=venda.data_compra.strftime("%H:%M"),
        forma_pagamento=venda.forma_pagamento,
        order_id=venda.id,
        conteudo=conteudo_str,
    )
    # Enviar como nova mensagem para não perder a tela de status
    await callback.message.answer(texto)

    # Botões para envio por email/whatsapp/telegram
    from keyboards.client import history_navigation_keyboard
    await callback.message.answer(
        "📧 Deseja receber por Email, WhatsApp ou ver no Telegram?",
        reply_markup=history_navigation_keyboard(1, 1, str(venda.id)),
    )


async def _processar_compra(callback: CallbackQuery, user_id, produto_id, quantidade=1):
    """Processa a compra com saldo, entregando os itens."""
    async with async_session() as session:
        async with session.begin():
            user = await _obter_usuario(session, user_id)
            produto = await _obter_produto(session, produto_id)

            if not user or not produto:
                await callback.message.edit_text(
                    "❌ Erro: usuário ou produto não encontrado.",
                    reply_markup=back_to_main_keyboard(),
                )
                await callback.answer()
                return

            if produto.estoque < quantidade:
                await callback.message.edit_text(
                    "❌ Estoque insuficiente.",
                    reply_markup=back_to_main_keyboard(),
                )
                await callback.answer()
                return

            preco_total = produto.preco * quantidade
            if user.saldo < preco_total:
                # Saldo insuficiente
                faltam = preco_total - user.saldo
                texto = get_message(
                    "saldo_insuficiente",
                    saldo=f"{float(user.saldo):.2f}",
                    preco=f"{float(preco_total):.2f}",
                    faltam=f"{float(faltam):.2f}",
                )
                await callback.message.edit_text(
                    texto,
                    reply_markup=insufficient_balance_keyboard(float(preco_total), produto_id, tipo="compra_multi" if quantidade > 1 else "compra"),
                )
                await callback.answer()
                return

            # Desconta saldo
            user.saldo -= preco_total
            user.total_gasto += preco_total

            # Seleciona itens do estoque e marca como vendidos
            conteudos = await _selecionar_itens_estoque(session, produto_id, quantidade)
            if not conteudos:
                # Rollback automático se não conseguir selecionar
                await session.rollback()
                await callback.message.edit_text(
                    "❌ Estoque insuficiente.",
                    reply_markup=back_to_main_keyboard(),
                )
                await callback.answer()
                return

            # Cria venda
            venda = await _criar_venda(
                session, user_id, produto, quantidade, preco_total, "saldo", conteudos
            )

            # Atualiza produto
            produto.estoque -= quantidade
            produto.vendidos += quantidade

            # Registra log
            log = Log(
                user_id=user_id,
                acao="compra_realizada",
                detalhes={
                    "produto_id": produto.id,
                    "quantidade": quantidade,
                    "valor_total": float(preco_total),
                    "venda_id": str(venda.id),
                },
            )
            session.add(log)
            await session.commit()

            await _entregar_produto(callback, user_id, venda, produto, conteudos)


@router.callback_query(F.data.startswith("comprar:"))
async def comprar_individual(callback: CallbackQuery):
    try:
        produto_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Produto inválido.", show_alert=True)
        return

    await _processar_compra(callback, callback.from_user.id, produto_id, quantidade=1)


@router.callback_query(F.data.startswith("comprar_multi:"))
async def comprar_multi(callback: CallbackQuery, state: FSMContext):
    try:
        produto_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Produto inválido.", show_alert=True)
        return

    # Armazena produto_id no estado
    await state.update_data(produto_id=produto_id)
    await state.set_state(PurchaseStates.waiting_quantity)

    async with async_session() as session:
        produto = await _obter_produto(session, produto_id)
        if produto:
            estoque = produto.estoque
        else:
            estoque = 0

    texto = (
        "Quantos logins deseja comprar?\n\n"
        f"📦 Estoque disponível: {estoque}\n\n"
        "💡 Digite /cancelar a qualquer momento para sair."
    )
    await callback.message.answer(texto)
    await callback.answer()


@router.message(PurchaseStates.waiting_quantity)
async def processar_quantidade(message: Message, state: FSMContext):
    if message.text == "/cancelar":
        await state.clear()
        await message.answer("Compra cancelada.")
        return

    try:
        quantidade = int(message.text)
        if quantidade <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Quantidade inválida. Digite um número inteiro positivo.")
        return

    data = await state.get_data()
    produto_id = data.get("produto_id")
    if not produto_id:
        await message.answer("❌ Erro: produto não identificado.")
        await state.clear()
        return

    # Processa compra com a quantidade
    # Precisamos de um callback-like, mas temos message; faremos adaptação
    # Criaremos um callback falso? Não, vamos processar diretamente.
    # Para manter a mesma lógica, faremos aqui o processamento com message.
    async with async_session() as session:
        async with session.begin():
            user = await _obter_usuario(session, message.from_user.id)
            produto = await _obter_produto(session, produto_id)

            if not user or not produto:
                await message.answer("❌ Erro: usuário ou produto não encontrado.")
                await state.clear()
                return

            if produto.estoque < quantidade:
                await message.answer(
                    f"❌ Quantidade indisponível.\n📦 Estoque disponível: {produto.estoque}"
                )
                await state.clear()
                return

            preco_total = produto.preco * quantidade
            if user.saldo < preco_total:
                faltam = preco_total - user.saldo
                texto = get_message(
                    "saldo_insuficiente_multi",
                    saldo=f"{float(user.saldo):.2f}",
                    total=f"{float(preco_total):.2f}",
                    faltam=f"{float(faltam):.2f}",
                )
                await message.answer(
                    texto,
                    reply_markup=insufficient_balance_keyboard(float(preco_total), produto_id, tipo="compra_multi"),
                )
                await state.clear()
                return

            # Saldo suficiente
            user.saldo -= preco_total
            user.total_gasto += preco_total

            conteudos = await _selecionar_itens_estoque(session, produto_id, quantidade)
            if not conteudos:
                await session.rollback()
                await message.answer("❌ Estoque insuficiente.")
                await state.clear()
                return

            venda = await _criar_venda(
                session, message.from_user.id, produto, quantidade, preco_total, "saldo", conteudos
            )

            produto.estoque -= quantidade
            produto.vendidos += quantidade

            log = Log(
                user_id=message.from_user.id,
                acao="compra_realizada",
                detalhes={
                    "produto_id": produto.id,
                    "quantidade": quantidade,
                    "valor_total": float(preco_total),
                    "venda_id": str(venda.id),
                },
            )
            session.add(log)
            await session.commit()

    # Enviar entrega (fora do bloco de sessão)
    async with async_session() as session:
        produto = await _obter_produto(session, produto_id)
        venda = await session.get(Venda, venda.id)
        conteudos = venda.itens_entregues or []
    # Precisamos de callback? Vamos enviar mensagens normais
    # Simular callback.message.answer usando message.answer
    if produto:
        conteudo_str = "\n\n".join(conteudos)
        texto = get_message(
            "compra_aprovada",
            produto=produto.nome,
            valor=f"{float(venda.valor_total):.2f}",
            data=venda.data_compra.strftime("%d/%m/%Y"),
            hora=venda.data_compra.strftime("%H:%M"),
            forma_pagamento=venda.forma_pagamento,
            order_id=venda.id,
            conteudo=conteudo_str,
        )
        await message.answer(texto)
        from keyboards.client import history_navigation_keyboard
        await message.answer(
            "📧 Deseja receber por Email, WhatsApp ou ver no Telegram?",
            reply_markup=history_navigation_keyboard(1, 1, str(venda.id)),
        )

    await state.clear()


@router.callback_query(F.data == "cancelar_compra")
async def cancelar_compra(callback: CallbackQuery):
    await callback.message.edit_text(
        "Compra cancelada.",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()
