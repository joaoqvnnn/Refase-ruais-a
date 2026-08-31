# ==============================================
# LARIZINHA STORE - HANDLER PROGRAMA DE AFILIADOS
# ==============================================

import logging
from datetime import datetime
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import User, Afiliado, SaqueAfiliado, Venda
from keyboards.client import affiliate_keyboard, back_to_main_keyboard
from texts.client import get_message
from config import BOT_USERNAME, MIN_WITHDRAWAL_VALUE, DEFAULT_AFFILIATE_COMMISSION
from utils.helpers import format_money, generate_uuid

logger = logging.getLogger(__name__)
router = Router()


class AffiliateStates(StatesGroup):
    waiting_withdrawal_value = State()
    waiting_pix_key = State()


async def _get_affiliate_data(user_id: int) -> dict:
    """
    Retorna os dados do afiliado para exibição.
    """
    async with async_session() as session:
        user = await session.get(User, user_id)
        afiliado = await session.get(Afiliado, user_id)

        if not afiliado:
            # Cria registro se não existir
            afiliado = Afiliado(
                user_id=user_id,
                comissao_percent=Decimal(str(DEFAULT_AFFILIATE_COMMISSION)),
                total_ganho=Decimal("0.00"),
                saldo_comissoes=Decimal("0.00"),
                total_indicacoes=0,
                nivel="Iniciante",
                meta_indicacoes=5,
            )
            session.add(afiliado)
            await session.commit()
            await session.refresh(afiliado)

        # Calcula média (se houver indicações)
        media = Decimal("0.00")
        if afiliado.total_indicacoes > 0:
            media = afiliado.total_ganho / afiliado.total_indicacoes

        # Próxima meta e restantes
        meta = afiliado.meta_indicacoes
        restantes = max(0, meta - afiliado.total_indicacoes)

        return {
            "comissao": float(afiliado.comissao_percent),
            "indicacoes": afiliado.total_indicacoes,
            "total_ganho": float(afiliado.total_ganho),
            "media": float(media),
            "saque_minimo": float(MIN_WITHDRAWAL_VALUE),
            "saldo_comissoes": float(afiliado.saldo_comissoes),
            "nivel": afiliado.nivel,
            "meta": meta,
            "restantes": restantes,
            "link": f"https://t.me/{BOT_USERNAME}?start={user_id}",
        }


@router.callback_query(F.data == "menu_affiliate")
async def menu_affiliate(callback: CallbackQuery):
    await show_affiliate_panel(callback)


async def show_affiliate_panel(callback: CallbackQuery) -> None:
    """
    Exibe o painel do afiliado com seus dados e link.
    """
    user_id = callback.from_user.id
    dados = await _get_affiliate_data(user_id)

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

    await callback.message.edit_text(texto, reply_markup=affiliate_keyboard())
    await callback.answer()


@router.callback_query(F.data == "solicitar_saque")
async def solicitar_saque(callback: CallbackQuery, state: FSMContext):
    """
    Inicia o fluxo de solicitação de saque.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        afiliado = await session.get(Afiliado, user_id)
        if not afiliado or afiliado.saldo_comissoes < Decimal(str(MIN_WITHDRAWAL_VALUE)):
            await callback.answer(
                f"Saldo insuficiente para saque.\nMínimo: R$ {MIN_WITHDRAWAL_VALUE:.2f}",
                show_alert=True,
            )
            return

    await state.set_state(AffiliateStates.waiting_withdrawal_value)
    await callback.message.answer(
        "💰 Solicitar Saque\n\n"
        f"Saldo disponível: R$ {float(afiliado.saldo_comissoes):.2f}\n"
        f"Saque mínimo: R$ {MIN_WITHDRAWAL_VALUE:.2f}\n\n"
        "Digite o valor que deseja sacar:"
    )
    await callback.answer()


@router.message(AffiliateStates.waiting_withdrawal_value)
async def processar_valor_saque(message: Message, state: FSMContext):
    """
    Recebe o valor do saque e pede a chave PIX.
    """
    try:
        valor = Decimal(message.text.replace(",", "."))
        if valor < Decimal(str(MIN_WITHDRAWAL_VALUE)):
            raise ValueError
    except (ValueError, Exception):
        await message.answer(
            f"❌ Valor inválido.\n"
            f"Saque mínimo: R$ {MIN_WITHDRAWAL_VALUE:.2f}\n"
            "Digite novamente:"
        )
        return

    user_id = message.from_user.id
    async with async_session() as session:
        afiliado = await session.get(Afiliado, user_id)
        if not afiliado or valor > afiliado.saldo_comissoes:
            await message.answer("❌ Saldo insuficiente para esse valor.")
            await state.clear()
            return

    await state.update_data(valor_saque=float(valor))
    await state.set_state(AffiliateStates.waiting_pix_key)
    await message.answer("🔑 Digite sua chave PIX para receber o saque:")


@router.message(AffiliateStates.waiting_pix_key)
async def processar_chave_pix(message: Message, state: FSMContext):
    """
    Recebe a chave PIX e registra a solicitação de saque.
    """
    chave_pix = message.text.strip()
    dados = await state.get_data()
    valor_saque = Decimal(str(dados.get("valor_saque", 0)))

    user_id = message.from_user.id

    async with async_session() as session:
        # Verifica saldo novamente
        afiliado = await session.get(Afiliado, user_id)
        if not afiliado or afiliado.saldo_comissoes < valor_saque:
            await message.answer("❌ Saldo insuficiente para esse valor.")
            await state.clear()
            return

        # Debita saldo de comissões
        afiliado.saldo_comissoes -= valor_saque

        # Cria solicitação
        saque = SaqueAfiliado(
            user_id=user_id,
            valor=valor_saque,
            chave_pix=chave_pix,
            status="pendente",
            data_solicitacao=datetime.now(),
        )
        session.add(saque)
        await session.commit()

    await message.answer(
        f"✅ Solicitação de saque registrada!\n\n"
        f"💰 Valor: R$ {float(valor_saque):.2f}\n"
        f"🔑 Chave PIX: {chave_pix}\n\n"
        "O saque será processado em breve."
    )
    await state.clear()


@router.callback_query(F.data == "historico_saques")
async def historico_saques(callback: CallbackQuery):
    """
    Exibe o histórico de saques do afiliado.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(SaqueAfiliado)
            .where(SaqueAfiliado.user_id == user_id)
            .order_by(SaqueAfiliado.data_solicitacao.desc())
        )
        saques = result.scalars().all()

    if not saques:
        texto = get_message(
            "saque_historico_vazio",
            saque_minimo=f"{MIN_WITHDRAWAL_VALUE:.2f}",
        )
        await callback.message.edit_text(texto, reply_markup=affiliate_keyboard())
        await callback.answer()
        return

    linhas = []
    for s in saques:
        linhas.append(
            f"💠 R$ {float(s.valor):.2f} - {s.status} ({s.data_solicitacao.strftime('%d/%m/%Y')})"
        )
    historico = "\n".join(linhas)

    await callback.message.edit_text(
        f"📊 HISTÓRICO DE SAQUES\n\n{historico}",
        reply_markup=affiliate_keyboard(),
    )
    await callback.answer()
