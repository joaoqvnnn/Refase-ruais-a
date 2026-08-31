# ==============================================
# LARIZINHA STORE - HANDLER HISTÓRICO DE COMPRAS
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from sqlalchemy import select, func
from database.connection import async_session
from database.models import Venda, Produto
from keyboards.client import history_navigation_keyboard, back_to_main_keyboard
from texts.client import get_message
from utils.helpers import format_money

logger = logging.getLogger(__name__)
router = Router()


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

        # Conteúdo dos itens entregues
        itens = venda.itens_entregues or []
        if itens:
            # Supõe que o conteúdo tenha email/senha separados por ":"
            primeiro = itens[0]
            partes = primeiro.split(":", 1)
            email = partes[0] if len(partes) > 0 else "N/A"
            senha = partes[1] if len(partes) > 1 else "N/A"
            nota = primeiro if len(partes) <= 1 else "Use o link abaixo para ativar:"
        else:
            email = "N/A"
            senha = "N/A"
            nota = "Sem conteúdo"

    return get_message(
        "historico_item",
        data=venda.data_compra.strftime("%d/%m/%Y"),
        vencimento=venda.vencimento.strftime("%d/%m/%Y") if venda.vencimento else "N/A",
        valor=f"{float(venda.valor_total):.2f}",
        id=str(venda.id)[:8],  # encurta para exibição
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
        await callback.message.edit_text(
            texto,
            reply_markup=profile_keyboard(),  # ou botão "Ver Todas"
        )
        # Adicionar botão "Ver Todas as Compras" seria melhor
        await callback.answer()
        return

    # Exibir primeira venda
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


@router.callback_query(F.data.startswith("enviar_email:"))
async def enviar_email(callback: CallbackQuery):
    venda_id = callback.data.split(":")[1]
    # Em produção: implementar envio de email com os dados da compra
    await callback.message.answer(
        "📧 Digite seu email para receber os dados da compra:",
    )
    # Podemos usar FSM para aguardar o email
    await callback.answer()


@router.callback_query(F.data.startswith("enviar_whatsapp:"))
async def enviar_whatsapp(callback: CallbackQuery):
    venda_id = callback.data.split(":")[1]
    # Em produção: implementar envio via WhatsApp
    await callback.message.answer(
        "📱 Digite seu número de WhatsApp para receber os dados:",
    )
    await callback.answer()


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
