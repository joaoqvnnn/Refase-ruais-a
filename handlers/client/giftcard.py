# ==============================================
# LARIZINHA STORE - HANDLER RESGATE DE GIFT CARD
# ==============================================

import logging
from datetime import datetime, date

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select
from database.connection import async_session
from database.models import User, GiftCard
from keyboards.client import giftcard_keyboard, back_to_main_keyboard
from texts.client import get_message

logger = logging.getLogger(__name__)
router = Router()


class GiftcardStates(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "giftcard")
async def giftcard_menu(callback: CallbackQuery, state: FSMContext):
    """
    Exibe a tela de resgate de gift card e aguarda o código.
    """
    await state.set_state(GiftcardStates.waiting_code)
    texto = get_message("giftcard")
    await callback.message.answer(texto, reply_markup=giftcard_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cancelar_giftcard")
async def cancelar_giftcard(callback: CallbackQuery, state: FSMContext):
    """
    Cancela a operação de resgate de gift card.
    """
    await state.clear()
    await callback.message.edit_text(
        "Operação cancelada.",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@router.message(GiftcardStates.waiting_code)
async def processar_codigo(message: Message, state: FSMContext):
    """
    Recebe o código do gift card, valida e credita saldo se válido.
    """
    codigo = message.text.strip().upper()

    async with async_session() as session:
        # Busca o gift card pelo código
        result = await session.execute(
            select(GiftCard).where(GiftCard.codigo == codigo)
        )
        giftcard = result.scalar_one_or_none()

        if not giftcard:
            await message.answer(get_message("giftcard_erro"))
            await state.clear()
            return

        if giftcard.usado:
            await message.answer("❌ Gift card já utilizado.")
            await state.clear()
            return

        if giftcard.expira_em and giftcard.expira_em < date.today():
            await message.answer("❌ Gift card expirado.")
            await state.clear()
            return

        # Credita o valor na carteira do usuário
        user = await session.get(User, message.from_user.id)
        if not user:
            await message.answer("Erro: usuário não encontrado.")
            await state.clear()
            return

        user.saldo += giftcard.valor
        user.total_gifts += giftcard.valor
        giftcard.usado = True
        giftcard.usado_por = user.id
        giftcard.data_uso = datetime.now()

        await session.commit()

        texto = get_message(
            "giftcard_sucesso",
            valor=f"{float(giftcard.valor):.2f}",
            saldo=f"{float(user.saldo):.2f}",
        )
        await message.answer(texto)

    await state.clear()
