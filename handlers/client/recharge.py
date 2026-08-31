# ==============================================
# LARIZINHA STORE - HANDLER RECARGA DE SALDO
# ==============================================

import logging
import base64
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.connection import async_session
from database.models import User, PagamentoPix, Log
from keyboards.client import (
    recharge_menu_keyboard,
    recharge_value_received_keyboard,
    payment_waiting_keyboard,
    back_to_main_keyboard,
)
from texts.client import get_message
from utils.helpers import generate_uuid
from config import (
    MIN_RECHARGE_VALUE,
    RECHARGE_BONUS_PERCENT,
    MIN_BONUS_VALUE,
    PIX_EXPIRATION_MINUTES,
)
from services.payment_gateway import create_pix_payment

logger = logging.getLogger(__name__)
router = Router()


class RechargeStates(StatesGroup):
    waiting_value = State()


async def show_recharge_menu(callback: CallbackQuery) -> None:
    """
    Exibe o menu de recarga com saldo atual.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

    texto = get_message(
        "recarga_inicio",
        user_id=user_id,
        saldo=f"{saldo:.2f}",
    )

    await callback.message.edit_text(texto, reply_markup=recharge_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_recharge")
async def menu_recharge(callback: CallbackQuery):
    await show_recharge_menu(callback)


@router.callback_query(F.data == "recarga_pix")
async def recarga_pix(callback: CallbackQuery, state: FSMContext):
    """
    Inicia o fluxo de recarga via PIX, aguardando o valor.
    """
    await state.set_state(RechargeStates.waiting_value)

    texto = get_message(
        "recarga_valor",
        minimo=f"{MIN_RECHARGE_VALUE:.2f}",
        bonus_percent=f"{RECHARGE_BONUS_PERCENT:.2f}",
        minimo_bonus=f"{MIN_BONUS_VALUE:.2f}",
    )

    await callback.message.answer(texto, reply_markup=recharge_value_received_keyboard())
    await callback.answer()


@router.message(RechargeStates.waiting_value)
async def processar_valor(message: Message, state: FSMContext):
    """
    Recebe o valor da recarga e gera o PIX.
    """
    try:
        valor = Decimal(message.text.replace(",", "."))
        if valor < Decimal(str(MIN_RECHARGE_VALUE)):
            raise ValueError
    except (ValueError, Exception):
        await message.answer(
            f"❌ Valor inválido.\n"
            f"🔻 Recarga mínima: R$ {MIN_RECHARGE_VALUE:.2f}\n"
            f"Digite novamente o valor desejado:"
        )
        return

    # Calcula bônus se aplicável
    bonus = Decimal("0.00")
    if valor >= Decimal(str(MIN_BONUS_VALUE)):
        bonus = (valor * Decimal(str(RECHARGE_BONUS_PERCENT)) / Decimal("100")).quantize(Decimal("0.01"))

    user_id = message.from_user.id

    # Cria cobrança PIX no gateway
    dados_pix = await create_pix_payment(
        valor=float(valor),
        user_id=user_id,
        description="Recarga Larizinha Store",
    )

    async with async_session() as session:
        pagamento = PagamentoPix(
            id=generate_uuid(),
            user_id=user_id,
            tipo="recarga",
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

        log = Log(
            user_id=user_id,
            acao="pix_recarga_gerado",
            detalhes={"valor": float(valor), "bonus": float(bonus), "pagamento_id": str(pagamento.id)},
        )
        session.add(log)
        await session.commit()

        user = await session.get(User, user_id)
        saldo_atual = float(user.saldo) if user else 0.0

    saldo_apos = saldo_atual + float(valor) + float(bonus)

    texto = get_message(
        "pix_gerado",
        minutos=PIX_EXPIRATION_MINUTES,
        valor=f"{float(valor):.2f}",
        payment_id=pagamento.id,
        codigo_pix=pagamento.codigo_pix or "",
        saldo=f"{saldo_atual:.2f}",
        bonus=f"{float(bonus):.2f}",
        saldo_apos=f"{saldo_apos:.2f}",
    )

    # Envia QR Code como imagem se disponível
    if pagamento.qr_code_base64:
        try:
            qr_bytes = base64.b64decode(pagamento.qr_code_base64)
            photo = BufferedInputFile(qr_bytes, filename="qrcode.png")
            await message.answer_photo(
                photo=photo,
                caption=texto,
                reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
            )
        except Exception:
            logger.exception("Erro ao enviar QR code como imagem.")
            await message.answer(
                texto,
                reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
            )
    else:
        await message.answer(
            texto,
            reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""),
        )

    await state.clear()


@router.callback_query(F.data == "cancelar_recarga")
async def cancelar_recarga(callback: CallbackQuery, state: FSMContext):
    """
    Cancela a recarga em andamento.
    """
    await state.clear()
    await callback.message.edit_text(
        "Recarga cancelada.",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()
