# ==============================================
# LARIZINHA STORE - HANDLER PAGAMENTOS PIX
# ==============================================

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.connection import async_session
from database.models import User, PagamentoPix, Log
from keyboards.client import payment_waiting_keyboard, back_to_main_keyboard
from texts.client import get_message
from config import PIX_EXPIRATION_MINUTES
from utils.helpers import generate_uuid, format_money

logger = logging.getLogger(__name__)
router = Router()


async def _criar_pagamento_pix(session, user_id, tipo, valor, bonus=0.0):
    """
    Cria um registro de pagamento PIX no banco com dados simulados.
    Em produção, essa função chamará o gateway real (Mercado Pago/Efí).
    """
    pagamento = PagamentoPix(
        id=generate_uuid(),
        user_id=user_id,
        tipo=tipo,
        valor=valor,
        bonus=bonus,
        status="pendente",
        codigo_pix="00020101021226830014BR.GOV.BCB.PIX...",
        qr_code_base64=None,
        txid=None,
        data_criacao=datetime.now(),
        data_expiracao=datetime.now() + timedelta(minutes=PIX_EXPIRATION_MINUTES),
    )
    session.add(pagamento)
    await session.flush()
    return pagamento


async def _enviar_mensagem_pix(callback: CallbackQuery, user_id, pagamento):
    """
    Monta e envia a mensagem com o PIX gerado, incluindo botões.
    """
    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

    valor = float(pagamento.valor)
    bonus = float(pagamento.bonus)
    saldo_apos = saldo + valor + bonus

    texto = get_message(
        "pix_gerado",
        minutos=PIX_EXPIRATION_MINUTES,
        valor=f"{valor:.2f}",
        payment_id=pagamento.id,
        codigo_pix=pagamento.codigo_pix,
        saldo=f"{saldo:.2f}",
        bonus=f"{bonus:.2f}",
        saldo_apos=f"{saldo_apos:.2f}",
    )

    await callback.message.answer_photo(
        photo=None,  # Em produção, enviar QR code gerado
        caption=texto,
        reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix),
    )


@router.callback_query(F.data.startswith("gerar_pix:"))
async def gerar_pix(callback: CallbackQuery):
    """
    Callback para gerar PIX a partir do botão de saldo insuficiente ou recarga.
    Formato do callback_data: gerar_pix:{tipo}:{produto_id}:{valor}
    """
    try:
        _, tipo, produto_id_str, valor_str = callback.data.split(":")
        produto_id = int(produto_id_str)
        valor = Decimal(valor_str)
    except Exception:
        await callback.answer("Dados inválidos para gerar PIX.", show_alert=True)
        return

    user_id = callback.from_user.id

    async with async_session() as session:
        # Para simplificar, criamos um pagamento de tipo "compra" ou "recarga"
        pagamento = await _criar_pagamento_pix(session, user_id, tipo, valor)

        # Registra log
        log = Log(
            user_id=user_id,
            acao="pix_gerado",
            detalhes={"tipo": tipo, "valor": float(valor), "pagamento_id": str(pagamento.id)},
        )
        session.add(log)
        await session.commit()

    await _enviar_mensagem_pix(callback, user_id, pagamento)
    await callback.answer()


@router.callback_query(F.data.startswith("verificar_pagamento:"))
async def verificar_pagamento(callback: CallbackQuery):
    """
    Callback para verificar se o PIX já foi pago.
    """
    pagamento_id = callback.data.split(":")[1]

    async with async_session() as session:
        pagamento = await session.get(PagamentoPix, pagamento_id)
        if not pagamento:
            await callback.answer("Pagamento não encontrado.", show_alert=True)
            return

        # Em produção: consultar gateway para confirmar pagamento
        # Simulação: verificar se expirou
        if pagamento.status == "pago":
            await callback.message.edit_text(
                "✅ Pagamento já confirmado! Seu saldo foi creditado."
            )
            await callback.answer()
            return

        if datetime.now() > pagamento.data_expiracao:
            # Marcar como expirado
            pagamento.status = "expirado"
            await session.commit()

            texto = get_message(
                "pagamento_expirado",
                payment_id=pagamento.id,
                valor=f"{float(pagamento.valor):.2f}",
            )
            from keyboards.client import recharge_menu_keyboard
            await callback.message.edit_text(
                texto,
                reply_markup=recharge_menu_keyboard(),
            )
            await callback.answer()
            return

        # Ainda pendente
        texto = get_message("pagamento_nao_identificado")
        await callback.message.edit_text(
            texto,
            reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix),
        )
        await callback.answer("Ainda não identificamos o pagamento.", show_alert=True)


@router.callback_query(F.data.startswith("copiar_pix:"))
async def copiar_pix(callback: CallbackQuery):
    """
    Callback para copiar o código PIX (apenas orienta o usuário).
    """
    pagamento_id = callback.data.split(":")[1]

    async with async_session() as session:
        pagamento = await session.get(PagamentoPix, pagamento_id)

    if pagamento:
        await callback.answer(
            "📋 Clique no código PIX na mensagem acima para copiar.",
            show_alert=True,
        )
    else:
        await callback.answer("Pagamento não encontrado.", show_alert=True)


@router.callback_query(F.data == "cancelar_pagamento")
async def cancelar_pagamento(callback: CallbackQuery):
    """
    Cancela um pagamento pendente.
    """
    # Como não temos o ID exato aqui, apenas voltamos ao menu.
    # Em uma implementação mais refinada, usaríamos o FSM para rastrear.
    await callback.message.edit_text(
        "Pagamento cancelado.",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()
