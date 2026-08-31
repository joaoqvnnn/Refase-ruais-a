# ==============================================
# LARIZINHA STORE - COMANDOS ESPECIAIS DO CLIENTE
# ==============================================

import logging
import base64
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command

from sqlalchemy import select
from database.connection import async_session
from database.models import User, PagamentoPix, Venda, Log
from keyboards.client import (
    main_menu_keyboard,
    payment_waiting_keyboard,
    back_to_main_keyboard,
)
from texts.client import get_message
from config import (
    MIN_RECHARGE_VALUE,
    RECHARGE_BONUS_PERCENT,
    MIN_BONUS_VALUE,
    PIX_EXPIRATION_MINUTES,
)
from utils.helpers import generate_uuid
from services.payment_gateway import create_pix_payment

logger = logging.getLogger(__name__)
router = Router()


# ---------- /id ----------
@router.message(Command("id"))
async def comando_id(message: Message):
    texto = get_message("comando_id", user_id=message.from_user.id)
    await message.answer(texto)


# ---------- /saldo ----------
@router.message(Command("saldo"))
async def comando_saldo(message: Message):
    user_id = message.from_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

    texto = get_message("comando_saldo", user_id=user_id, saldo=f"{saldo:.2f}")
    await message.answer(texto)


# ---------- /pix ----------
@router.message(Command("pix"))
async def comando_pix(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(get_message("comando_pix_uso"))
        return

    try:
        valor = Decimal(parts[1].replace(",", "."))
        if valor < Decimal(str(MIN_RECHARGE_VALUE)):
            raise ValueError
    except (ValueError, Exception):
        await message.answer(get_message("comando_pix_uso"))
        return

    # Calcula bônus
    bonus = Decimal("0.00")
    if valor >= Decimal(str(MIN_BONUS_VALUE)):
        bonus = (valor * Decimal(str(RECHARGE_BONUS_PERCENT)) / Decimal("100")).quantize(Decimal("0.01"))

    user_id = message.from_user.id

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
            logger.exception("Erro ao enviar QR code no /pix")
            await message.answer(texto, reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""))
    else:
        await message.answer(texto, reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix or ""))


# ---------- /historico ----------
@router.message(Command("historico"))
async def comando_historico(message: Message):
    user_id = message.from_user.id
    async with async_session() as session:
        result = await session.execute(
            select(Venda)
            .where(Venda.user_id == user_id, Venda.status == "pago")
            .order_by(Venda.data_compra.desc())
            .limit(1)
        )
        venda = result.scalar_one_or_none()

    if not venda:
        await message.answer("Você ainda não possui compras.", reply_markup=main_menu_keyboard())
        return

    from handlers.client.history import _formatar_item_historico
    texto = await _formatar_item_historico(venda)
    from keyboards.client import history_navigation_keyboard
    await message.answer(texto, reply_markup=history_navigation_keyboard(1, 1, str(venda.id)))


# ---------- /alerta ----------
@router.message(Command("alerta"))
async def comando_alerta(message: Message):
    from handlers.client.alerts import _montar_lista_produtos_alertas
    texto, teclado, _ = await _montar_lista_produtos_alertas(message.from_user.id, 0)
    await message.answer(texto, reply_markup=teclado)


# ---------- /afiliados ----------
@router.message(Command("afiliados"))
async def comando_afiliados(message: Message):
    from handlers.client.affiliate import _get_affiliate_data
    dados = await _get_affiliate_data(message.from_user.id)

    texto = get_message(
        "afiliados",
        comissao=f"{dados['comissao']:.1f}",
        indicacoes=dados["indicacoes"],
        total_ganho=f"{dados['total_ganho']:.2f}",
        media=f"{dados['media']:.2f}",
        saque_minimo=f"{dados['saque_minimo']:.2f}",
        saldo_comissoes=f"{dados['saldo_comissoes']:.2f}",
        nivel=dados["nivel"],
        meta=dados["meta"],
        restantes=dados["restantes"],
        link=dados["link"],
    )
    from keyboards.client import affiliate_keyboard
    await message.answer(texto, reply_markup=affiliate_keyboard())


# ---------- /ranking ----------
@router.message(Command("ranking"))
async def comando_ranking(message: Message):
    from aiogram.types import CallbackQuery
    from handlers.client.rankings import show_rankings

    class FakeCallback:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
        async def answer(self, *args, **kwargs):
            pass

    await show_rankings(FakeCallback(message), "servicos")


# ---------- /termos ----------
@router.message(Command("termos"))
async def comando_termos(message: Message):
    await message.answer(get_message("termos"), reply_markup=back_to_main_keyboard())


# ---------- /suporte ----------
@router.message(Command("suporte"))
async def comando_suporte(message: Message):
    await message.answer(get_message("suporte", whatsapp="449986915568", email="suporte@larizinha.com"), reply_markup=back_to_main_keyboard())


# ---------- /cancelar ----------
@router.message(Command("cancelar"))
async def comando_cancelar(message: Message):
    await message.answer("Operação cancelada.", reply_markup=main_menu_keyboard())
