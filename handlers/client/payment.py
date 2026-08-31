# ==============================================
# LARIZINHA STORE - HANDLER PAGAMENTOS PIX
# ==============================================

import logging
import base64
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

from database.connection import async_session
from database.models import User, PagamentoPix, Log
from keyboards.client import payment_waiting_keyboard, back_to_main_keyboard
from texts.client import get_message
from config import PIX_EXPIRATION_MINUTES
from utils.helpers import generate_uuid
from services.payment_gateway import create_pix_payment, check_payment_status

logger = logging.getLogger(__name__)
router = Router()


async def _criar_registro_pagamento(session, user_id, tipo, valor, dados_pix, bonus=0.0):
    """
    Cria o registro de pagamento PIX no banco a partir dos dados do gateway.
    """
    pagamento = PagamentoPix(
        id=generate_uuid(),
        user_id=user_id,
        tipo=tipo,
        valor=valor,
        bonus=bonus,
        status="pendente",
        codigo_pix=dados_pix.get("codigo_pix"),
        qr_code_base64=dados_pix.get("qr_code_base64"),
        txid=dados_pix.get("txid"),
        data_criacao=datetime.now(),
        data_expiracao=dados_pix.get("data_expiracao") or (datetime.now() + timedelta(minutes=PIX_EXPIRATION_MINUTES)),
    )
    session.add(pagamento)
    await session.flush()
    return pagamento


async def _enviar_mensagem_pix(callback: CallbackQuery, user_id, pagamento):
    """
    Monta e envia a mensagem com o PIX gerado, incluindo QR Code como imagem.
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
        codigo_pix=pagamento.codigo_pix or "",
        saldo=f"{saldo:.2f}",
        bonus=f"{bonus:.2f}",
        saldo_apos=f"{saldo_apos:.2f}",
    )

    # Se houver QR code base64, envia como foto
    if pagamento.qr_code_base64:
        try:
            qr_bytes = base64.b64decode(pagamento.qr_code_base64)
            photo = BufferedInputFile(qr_bytes, filename="qrcode.png")
            await callback.message.answer_photo(
                photo=photo,
                caption=texto,
                reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
            )
        except Exception as e:
            logger.exception("Erro ao enviar QR code como imagem, enviando apenas texto.")
            await callback.message.answer(
                texto,
                reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
            )
    else:
        await callback.message.answer(
            texto,
            reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
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

    # Cria cobrança no gateway (real ou simulada)
    dados_pix = await create_pix_payment(
        valor=float(valor),
        user_id=user_id,
        description="Recarga Larizinha Store" if tipo == "recarga" else "Compra Larizinha Store",
    )

    async with async_session() as session:
        pagamento = await _criar_registro_pagamento(session, user_id, tipo, valor, dados_pix)
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

        if pagamento.status == "pago":
            await callback.message.edit_text("✅ Pagamento já confirmado! Seu saldo foi creditado.")
            await callback.answer()
            return

        if datetime.now() > pagamento.data_expiracao:
            pagamento.status = "expirado"
            await session.commit()

            texto = get_message(
                "pagamento_expirado",
                payment_id=pagamento.id,
                valor=f"{float(pagamento.valor):.2f}",
            )
            from keyboards.client import recharge_menu_keyboard
            await callback.message.edit_text(texto, reply_markup=recharge_menu_keyboard())
            await callback.answer()
            return

        # Consulta status no gateway
        status = await check_payment_status(pagamento.txid) if pagamento.txid else "pendente"

        if status == "pago":
            pagamento.status = "pago"
            pagamento.data_pagamento = datetime.now()

            if pagamento.tipo == "recarga":
                user = await session.get(User, pagamento.user_id)
                if user:
                    user.saldo += pagamento.valor + pagamento.bonus
                    user.total_recargas += pagamento.valor

            log = Log(
                user_id=pagamento.user_id,
                acao="pagamento_confirmado_manual",
                detalhes={"payment_id": str(pagamento.id)},
            )
            session.add(log)
            await session.commit()

            await callback.message.edit_text("✅ Pagamento confirmado!")
            await callback.answer()
            return

        # Ainda pendente
        texto = get_message("pagamento_nao_identificado")
        await callback.message.edit_text(
            texto,
            reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
        )
        await callback.answer("Ainda não identificamos o pagamento.", show_alert=True)


@router.callback_query(F.data.startswith("copiar_pix:"))
async def copiar_pix(callback: CallbackQuery):
    """
    Callback para copiar o código PIX.
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
    await callback.message.edit_text(
        "Pagamento cancelado.",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()
