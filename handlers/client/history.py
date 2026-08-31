# ==============================================
# LARIZINHA STORE - HANDLER HISTÓRICO DE COMPRAS
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select
from database.connection import async_session
from database.models import Venda, Produto
from keyboards.client import history_navigation_keyboard, back_to_main_keyboard
from texts.client import get_message
from services.notifier import send_email, send_whatsapp
from utils.helpers import format_money

logger = logging.getLogger(__name__)
router = Router()


class HistoryStates(StatesGroup):
    waiting_email = State()
    waiting_whatsapp = State()


async def _obter_vendas_usuario(user_id: int, apenas_ativas: bool = False) -> list[Venda]:
    """
    Retorna as vendas do usuário, opcionalmente filtrando apenas as não vencidas.
    """
    async with async_session() as session:
        query = select(Venda).where(Venda.user_id == user_id, Venda.status == "pago")
        if apenas_ativas:
            query = query.where(Venda.vencimento >= func.current_date())
        query = query.order_by(Venda.data_compra.desc())
        result = await session.execute(query)
        return result.scalars().all()


async def _formatar_item_historico(venda: Venda) -> str:
    """
    Formata uma venda para exibição no histórico.
    """
    async with async_session() as session:
        produto = await session.get(Produto, venda.produto_id)
        nome_produto = produto.nome if produto else "Produto removido"

        itens = venda.itens_entregues or []
        if itens:
            primeiro = itens[0]
            partes = primeiro.split(":", 1)
            email = partes[0] if len(partes) > 0 else "N/A"
            senha = partes[1] if len(partes) > 1 else "N/A"
            nota = "Use o link abaixo para ativar:" if len(partes) <= 1 else primeiro
        else:
            email = "N/A"
            senha = "N/A"
            nota = "Sem conteúdo"

    return get_message(
        "historico_item",
        data=venda.data_compra.strftime("%d/%m/%Y"),
        vencimento=venda.vencimento.strftime("%d/%m/%Y") if venda.vencimento else "N/A",
        valor=f"{float(venda.valor_total):.2f}",
        id=str(venda.id)[:8],
        nome_produto=nome_produto,
        email=email,
        senha=senha,
        nota=nota,
        referencia=email,
    )


@router.callback_query(F.data == "historico")
async def historico_compras(callback: CallbackQuery):
    """
    Exibe o histórico de compras ativas (não vencidas).
    """
    user_id = callback.from_user.id
    vendas = await _obter_vendas_usuario(user_id, apenas_ativas=True)

    if not vendas:
        texto = get_message("historico_vazio")
        from keyboards.client import profile_keyboard
        await callback.message.edit_text(texto, reply_markup=profile_keyboard())
        await callback.answer()
        return

    venda = vendas[0]
    texto = await _formatar_item_historico(venda)
    texto = f"🛍 Compras: 1/{len(vendas)}\n\n" + texto

    await callback.message.edit_text(
        texto,
        reply_markup=history_navigation_keyboard(1, len(vendas), str(venda.id)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hist_ant:"))
async def hist_anterior(callback: CallbackQuery):
    indice = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    vendas = await _obter_vendas_usuario(user_id)

    if indice > 1:
        novo_indice = indice - 1
        venda = vendas[novo_indice - 1]
        texto = await _formatar_item_historico(venda)
        texto = f"🛍 Compras: {novo_indice}/{len(vendas)}\n\n" + texto
        await callback.message.edit_text(
            texto,
            reply_markup=history_navigation_keyboard(novo_indice, len(vendas), str(venda.id)),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("hist_prox:"))
async def hist_proxima(callback: CallbackQuery):
    indice = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    vendas = await _obter_vendas_usuario(user_id)

    if indice < len(vendas):
        novo_indice = indice + 1
        venda = vendas[novo_indice - 1]
        texto = await _formatar_item_historico(venda)
        texto = f"🛍 Compras: {novo_indice}/{len(vendas)}\n\n" + texto
        await callback.message.edit_text(
            texto,
            reply_markup=history_navigation_keyboard(novo_indice, len(vendas), str(venda.id)),
        )
    await callback.answer()


# ---------- ENVIO POR EMAIL ----------
@router.callback_query(F.data.startswith("enviar_email:"))
async def enviar_email(callback: CallbackQuery, state: FSMContext):
    venda_id = callback.data.split(":")[1]
    await state.update_data(venda_id=venda_id)
    await state.set_state(HistoryStates.waiting_email)
    await callback.message.answer("📧 Digite seu e-mail para receber os dados da compra:")
    await callback.answer()


@router.message(HistoryStates.waiting_email)
async def processar_email(message: Message, state: FSMContext):
    email = message.text.strip()
    if not email or "@" not in email:
        await message.answer("E-mail inválido. Digite novamente ou /cancelar.")
        return

    dados = await state.get_data()
    venda_id = dados.get("venda_id")

    async with async_session() as session:
        venda = await session.get(Venda, venda_id)
        produto = await session.get(Produto, venda.produto_id) if venda else None

    if not venda or not produto:
        await message.answer("Venda não encontrada.")
        await state.clear()
        return

    conteudo = "\n".join(venda.itens_entregues or [])
    corpo = (
        f"🛍 {produto.nome}\n"
        f"💰 Valor: R$ {float(venda.valor_total):.2f}\n"
        f"📅 Data: {venda.data_compra.strftime('%d/%m/%Y')}\n"
        f"🎫 ID: {venda.id}\n\n"
        f"Dados de acesso:\n{conteudo}"
    )

    enviado = await send_email(email, f"Sua compra - {produto.nome}", corpo)
    if enviado:
        await message.answer("✅ Dados enviados para seu e-mail!")
    else:
        await message.answer("❌ Falha ao enviar e-mail. Tente novamente mais tarde.")
    await state.clear()


# ---------- ENVIO POR WHATSAPP ----------
@router.callback_query(F.data.startswith("enviar_whatsapp:"))
async def enviar_whatsapp(callback: CallbackQuery, state: FSMContext):
    venda_id = callback.data.split(":")[1]
    await state.update_data(venda_id=venda_id)
    await state.set_state(HistoryStates.waiting_whatsapp)
    await callback.message.answer("📱 Digite seu número de WhatsApp (com DDI e DDD) para receber os dados:")
    await callback.answer()


@router.message(HistoryStates.waiting_whatsapp)
async def processar_whatsapp(message: Message, state: FSMContext):
    numero = message.text.strip()
    # Remove caracteres não numéricos, mantém o que for válido para API
    numero_limpo = ''.join(filter(str.isdigit, numero))
    if len(numero_limpo) < 10:
        await message.answer("Número inválido. Digite novamente ou /cancelar.")
        return

    dados = await state.get_data()
    venda_id = dados.get("venda_id")

    async with async_session() as session:
        venda = await session.get(Venda, venda_id)
        produto = await session.get(Produto, venda.produto_id) if venda else None

    if not venda or not produto:
        await message.answer("Venda não encontrada.")
        await state.clear()
        return

    conteudo = "\n".join(venda.itens_entregues or [])
    mensagem_whats = (
        f"🛍 *{produto.nome}*\n"
        f"💰 *Valor:* R$ {float(venda.valor_total):.2f}\n"
        f"📅 *Data:* {venda.data_compra.strftime('%d/%m/%Y')}\n"
        f"🎫 *ID:* {venda.id}\n\n"
        f"Dados de acesso:\n{conteudo}"
    )

    enviado = await send_whatsapp(numero_limpo, mensagem_whats)
    if enviado:
        await message.answer("✅ Dados enviados para seu WhatsApp!")
    else:
        await message.answer("❌ Falha ao enviar WhatsApp. Tente novamente mais tarde.")
    await state.clear()


# ---------- MOSTRAR CONTEÚDO NO TELEGRAM ----------
@router.callback_query(F.data.startswith("mostrar_conteudo:"))
async def mostrar_conteudo(callback: CallbackQuery):
    venda_id = callback.data.split(":")[1]
    async with async_session() as session:
        venda = await session.get(Venda, venda_id)
        if venda and venda.itens_entregues:
            conteudo = "\n\n".join(venda.itens_entregues)
            await callback.message.answer(f"🔐 Conteúdo da compra:\n\n{conteudo}")
        else:
            await callback.message.answer("Conteúdo não encontrado.")
    await callback.answer()
