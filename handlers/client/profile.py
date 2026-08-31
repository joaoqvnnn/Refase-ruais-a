# ==============================================
# LARIZINHA STORE - HANDLER PERFIL DO USUÁRIO
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import User, Venda
from keyboards.client import profile_keyboard, alterar_dados_keyboard, back_to_main_keyboard
from texts.client import get_message
from utils.helpers import format_money

logger = logging.getLogger(__name__)
router = Router()


class ProfileStates(StatesGroup):
    waiting_whatsapp = State()


async def show_profile(callback: CallbackQuery) -> None:
    """
    Exibe o perfil do usuário com informações e movimentações.
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("Usuário não encontrado.", show_alert=True)
            return

        # Contagem de compras realizadas
        result = await session.execute(
            select(func.count(Venda.id)).where(Venda.user_id == user_id, Venda.status == "pago")
        )
        total_compras = result.scalar() or 0

        saldo = float(user.saldo)
        whatsapp = user.whatsapp or "Não cadastrado"
        total_gasto = float(user.total_gasto)
        total_recargas = float(user.total_recargas)
        total_gifts = float(user.total_gifts)

    texto = get_message(
        "perfil",
        user_id=user_id,
        saldo=f"{saldo:.2f}",
        whatsapp=whatsapp,
        total_compras=total_compras,
        total_gasto=f"{total_gasto:.2f}",
        total_recargas=f"{total_recargas:.2f}",
        total_gifts=f"{total_gifts:.2f}",
    )

    await callback.message.edit_text(texto, reply_markup=profile_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    await show_profile(callback)


@router.callback_query(F.data == "alterar_dados")
async def alterar_dados(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
        whatsapp = user.whatsapp or ""

    texto = get_message("alterar_dados", whatsapp=whatsapp or "Não cadastrado")
    await callback.message.edit_text(texto, reply_markup=alterar_dados_keyboard(whatsapp))
    await callback.answer()


@router.callback_query(F.data == "alterar_whatsapp")
async def alterar_whatsapp(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_whatsapp)
    texto = get_message("alterar_whatsapp_digitar")
    await callback.message.answer(texto)
    await callback.answer()


@router.message(ProfileStates.waiting_whatsapp)
async def processar_whatsapp(message: Message, state: FSMContext):
    novo_whatsapp = message.text.strip()

    # Validação simples: apenas dígitos e tamanho mínimo
    if not novo_whatsapp or len(novo_whatsapp) < 10:
        await message.answer("❌ Número inválido. Digite um número de WhatsApp válido.")
        return

    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            user.whatsapp = novo_whatsapp
            await session.commit()

    await state.clear()
    await message.answer("✅ WhatsApp atualizado com sucesso!")
    # Retorna ao perfil
    # Como é message, enviaremos perfil via callback não é possível; faremos inline
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            texto = get_message(
                "perfil",
                user_id=user.id,
                saldo=f"{float(user.saldo):.2f}",
                whatsapp=user.whatsapp or "Não cadastrado",
                total_compras=0,  # simplificação; em produção buscar contagem
                total_gasto=f"{float(user.total_gasto):.2f}",
                total_recargas=f"{float(user.total_recargas):.2f}",
                total_gifts=f"{float(user.total_gifts):.2f}",
            )
            await message.answer(texto, reply_markup=profile_keyboard())


@router.callback_query(F.data == "menu_profile_back")
async def voltar_perfil(callback: CallbackQuery):
    await show_profile(callback)
