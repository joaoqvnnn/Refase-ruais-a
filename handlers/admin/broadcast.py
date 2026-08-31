# ==============================================
# LARIZINHA STORE - HANDLER ADMIN BROADCAST
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import User, Log
from keyboards.admin import admin_broadcast_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA BROADCAST
# ==============================================
class BroadcastForm(StatesGroup):
    waiting_target = State()           # "all" ou "user" (definido pelo callback inicial)
    waiting_user_id = State()          # apenas se target == "user"
    waiting_message = State()
    waiting_confirmation = State()


# ==============================================
# MENU PRINCIPAL DE BROADCAST
# ==============================================
@router.callback_query(F.data == "admin_broadcast")
@admin_only
async def admin_broadcast_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📨 Enviar Broadcast\n\n"
        "Escolha o público-alvo:",
        reply_markup=admin_broadcast_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# INICIAR BROADCAST PARA TODOS
# ==============================================
@router.callback_query(F.data == "admin_broadcast_all")
@admin_only
async def admin_broadcast_all(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target="all")
    await state.set_state(BroadcastForm.waiting_message)
    await callback.message.answer(
        "Digite a mensagem que deseja enviar para todos os usuários:"
    )
    await callback.answer()


# ==============================================
# INICIAR BROADCAST PARA UM USUÁRIO
# ==============================================
@router.callback_query(F.data == "admin_broadcast_user")
@admin_only
async def admin_broadcast_user(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target="user")
    await state.set_state(BroadcastForm.waiting_user_id)
    await callback.message.answer("Digite o ID do Telegram do usuário:")
    await callback.answer()


@router.message(BroadcastForm.waiting_user_id)
@admin_only
async def broadcast_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID inválido. Digite um número.")
        return

    await state.update_data(target_user_id=user_id)
    await state.set_state(BroadcastForm.waiting_message)
    await message.answer(f"Digite a mensagem que deseja enviar ao usuário #{user_id}:")


# ==============================================
# RECEBER MENSAGEM DO BROADCAST
# ==============================================
@router.message(BroadcastForm.waiting_message)
@admin_only
async def broadcast_message_received(message: Message, state: FSMContext):
    texto = message.text.strip()
    if not texto:
        await message.answer("Mensagem vazia. Digite um texto.")
        return

    await state.update_data(message_text=texto)
    await state.set_state(BroadcastForm.waiting_confirmation)

    dados = await state.get_data()
    alvo = dados.get("target")
    if alvo == "all":
        descricao = "todos os usuários"
    else:
        descricao = f"usuário #{dados.get('target_user_id')}"

    await message.answer(
        f"Confirma envio para <b>{descricao}</b>?\n\n"
        "Pré-visualização:\n"
        f"<pre>{texto}</pre>\n\n"
        "Envie /confirmar para enviar ou /cancelar para abortar."
    )


# ==============================================
# CONFIRMAÇÃO E ENVIO
# ==============================================
@router.message(BroadcastForm.waiting_confirmation)
@admin_only
async def broadcast_confirmation(message: Message, state: FSMContext):
    if message.text.strip() == "/cancelar":
        await state.clear()
        await message.answer("Broadcast cancelado.")
        return

    if message.text.strip() != "/confirmar":
        await message.answer("Envie /confirmar para enviar ou /cancelar para abortar.")
        return

    dados = await state.get_data()
    texto = dados["message_text"]
    alvo = dados.get("target")

    # Executa envio
    if alvo == "all":
        # Busca todos os IDs
        async with async_session() as session:
            result = await session.execute(select(User.id))
            user_ids = [row[0] for row in result.all()]

        enviados = 0
        falhas = 0
        for uid in user_ids:
            try:
                await message.bot.send_message(chat_id=uid, text=texto)
                enviados += 1
            except Exception as e:
                falhas += 1
                logger.warning(f"Falha ao enviar broadcast para {uid}: {e}")

        # Log
        async with async_session() as session:
            log = Log(
                user_id=message.from_user.id,
                acao="broadcast_enviado",
                detalhes={
                    "alvo": "todos",
                    "total": len(user_ids),
                    "enviados": enviados,
                    "falhas": falhas,
                }
            )
            session.add(log)
            await session.commit()

        await message.answer(
            f"✅ Broadcast concluído!\n\n"
            f"Total: {len(user_ids)}\n"
            f"Enviados: {enviados}\n"
            f"Falhas: {falhas}"
        )

    else:  # alvo == "user"
        uid = dados.get("target_user_id")
        try:
            await message.bot.send_message(chat_id=uid, text=texto)
            await message.answer(f"✅ Mensagem enviada ao usuário #{uid}.")
            # Log
            async with async_session() as session:
                log = Log(
                    user_id=message.from_user.id,
                    acao="broadcast_enviado",
                    detalhes={"alvo": "usuario", "user_id": uid}
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            await message.answer(f"❌ Falha ao enviar para #{uid}: {e}")

    await state.clear()
