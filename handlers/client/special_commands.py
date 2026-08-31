# ==============================================
# LARIZINHA STORE - COMANDOS ESPECIAIS DO CLIENTE
# ==============================================

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from sqlalchemy import select, func
from database.connection import async_session
from database.models import User, Venda, PagamentoPix, GiftCard, Alerta, Afiliado
from keyboards.client import (
    main_menu_keyboard,
    history_navigation_keyboard,
    back_to_main_keyboard,
    recharge_menu_keyboard,
    payment_waiting_keyboard,
)
from texts.client import get_message
from config import (
    BOT_USERNAME,
    MIN_RECHARGE_VALUE,
    RECHARGE_BONUS_PERCENT,
    MIN_BONUS_VALUE,
    PIX_EXPIRATION_MINUTES,
)
from utils.helpers import generate_uuid

logger = logging.getLogger(__name__)
router = Router()


# ---------- /id ----------
@router.message(Command("id"))
async def comando_id(message: Message):
    """Mostra o ID do Telegram do usuário."""
    texto = get_message("comando_id", user_id=message.from_user.id)
    await message.answer(texto)


# ---------- /saldo ----------
@router.message(Command("saldo"))
async def comando_saldo(message: Message):
    """Mostra o saldo atual da carteira."""
    user_id = message.from_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
        saldo = float(user.saldo) if user else 0.0

    texto = get_message("comando_saldo", user_id=user_id, saldo=f"{saldo:.2f}")
    await message.answer(texto)


# ---------- /pix ----------
@router.message(Command("pix"))
async def comando_pix(message: Message):
    """Gera um PIX de recarga com o valor informado. Uso: /pix 10 ou /pix 5.25"""
    parts = message.text.split()
    if len(parts) < 2:
        texto = get_message("comando_pix_uso")
        await message.answer(texto)
        return

    try:
        valor = Decimal(parts[1].replace(",", "."))
        if valor < Decimal(str(MIN_RECHARGE_VALUE)):
            raise ValueError
    except (ValueError, Exception):
        texto = get_message("comando_pix_uso")
        await message.answer(texto)
        return

    # Calcula bônus
    bonus = Decimal("0.00")
    if valor >= Decimal(str(MIN_BONUS_VALUE)):
        bonus = (valor * Decimal(str(RECHARGE_BONUS_PERCENT)) / Decimal("100")).quantize(Decimal("0.01"))

    user_id = message.from_user.id

    async with async_session() as session:
        pagamento = PagamentoPix(
            id=generate_uuid(),
            user_id=user_id,
            tipo="recarga",
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
        await session.commit()

        user = await session.get(User, user_id)
        saldo_atual = float(user.saldo) if user else 0.0

    saldo_apos = saldo_atual + float(valor) + float(bonus)

    texto = get_message(
        "pix_gerado",
        minutos=PIX_EXPIRATION_MINUTES,
        valor=f"{float(valor):.2f}",
        payment_id=pagamento.id,
        codigo_pix=pagamento.codigo_pix,
        saldo=f"{saldo_atual:.2f}",
        bonus=f"{float(bonus):.2f}",
        saldo_apos=f"{saldo_apos:.2f}",
    )

    await message.answer(
        texto,
        reply_markup=payment_waiting_keyboard(str(pagamento.id), pagamento.codigo_pix),
    )


# ---------- /historico ----------
@router.message(Command("historico"))
async def comando_historico(message: Message):
    """Atalho para o histórico de compras."""
    # Reutiliza o handler de histórico, mas é mais simples enviar uma chamada ao menu
    # Vamos importar e chamar a função show_history? Ela requer callback.
    # Melhor enviar mensagem com primeira compra, se houver.
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
        await message.answer(
            "Você ainda não possui compras.",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Formatar com base no template
    from handlers.client.history import _formatar_item_historico
    texto = await _formatar_item_historico(venda)
    await message.answer(texto, reply_markup=history_navigation_keyboard(1, 1, str(venda.id)))


# ---------- /alerta ----------
@router.message(Command("alerta"))
async def comando_alerta(message: Message):
    """Abre o sistema de alertas de reabastecimento."""
    # Reutiliza o handler de alertas, mas como não temos callback,
    # montamos a tela manualmente.
    from handlers.client.alerts import _montar_lista_produtos_alertas
    texto, teclado, _ = await _montar_lista_produtos_alertas(message.from_user.id, 0)
    await message.answer(texto, reply_markup=teclado)


# ---------- /afiliados ----------
@router.message(Command("afiliados"))
async def comando_afiliados(message: Message):
    """Abre o painel de afiliados."""
    # Reutiliza a função do handler de afiliados
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
    """Abre os rankings."""
    # Reutiliza a função de rankings
    from handlers.client.rankings import show_rankings
    # show_rankings requer callback, não message. Faremos uma chamada direta.
    # Para simplificar, enviamos mensagem com botões e chamamos o primeiro ranking.
    # Mas show_rankings espera callback. Vamos adaptar criando um mini-callback?
    # Alternativa: enviar a tela de rankings com a aba de serviços.
    from aiogram.types import CallbackQuery
    # Criar um callback fictício não é fácil; melhor replicar consulta.
    # Vamos delegar para a função interna que retorna texto e teclado.
    # Por ora, exibiremos a tela com o teclado e uma mensagem simples.
    # Melhor: chamar show_rankings com um objeto que tenha message.
    # Vamos criar um "fake callback" só para reuso.
    class FakeCallback:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
        async def answer(self, *args, **kwargs):
            pass

    fake_callback = FakeCallback(message)
    await show_rankings(fake_callback, "servicos")


# ---------- /termos ----------
@router.message(Command("termos"))
async def comando_termos(message: Message):
    """Exibe os termos de uso."""
    texto = get_message("termos")
    await message.answer(texto, reply_markup=back_to_main_keyboard())


# ---------- /suporte ----------
@router.message(Command("suporte"))
async def comando_suporte(message: Message):
    """Exibe informações de atendimento."""
    texto = get_message("suporte", whatsapp="449986915568", email="suporte@larizinha.com")
    await message.answer(texto, reply_markup=back_to_main_keyboard())


# ---------- /cancelar (para uso em estados FSM) ----------
@router.message(Command("cancelar"))
async def comando_cancelar(message: Message):
    """Cancela a operação atual (se houver)."""
    await message.answer("Operação cancelada.", reply_markup=main_menu_keyboard())
