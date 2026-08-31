# ==============================================
# LARIZINHA STORE - HANDLER ADMIN USUÁRIOS
# ==============================================

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func, update
from database.connection import async_session
from database.models import User, Venda, Log
from keyboards.admin import admin_users_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only
from utils.validators import validar_id_telegram

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA AÇÕES COM USUÁRIO
# ==============================================
class UserActionForm(StatesGroup):
    waiting_user_id = State()
    waiting_adjust_value = State()
    waiting_adjust_reason = State()
    waiting_message_text = State()
    waiting_confirm = State()


# ==============================================
# MENU PRINCIPAL DE USUÁRIOS
# ==============================================
@router.callback_query(F.data == "admin_users")
@admin_only
async def admin_users_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 Gerenciar Usuários\n\n"
        "Escolha uma ação:",
        reply_markup=admin_users_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR ÚLTIMOS USUÁRIOS
# ==============================================
@router.callback_query(F.data == "admin_user_list")
@admin_only
async def admin_user_list(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.data_cadastro.desc()).limit(10)
        )
        users = result.scalars().all()

    if not users:
        texto = "Nenhum usuário cadastrado."
        teclado = admin_users_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for u in users:
            nome = u.first_name or u.username or str(u.id)
            linhas.append(f"#{u.id} {nome} | Saldo: R$ {float(u.saldo):.2f}")
            botoes.append([
                InlineKeyboardButton(text=f"👁 {nome}", callback_data=f"admin_user_view:{u.id}"),
                InlineKeyboardButton(text="💰", callback_data=f"admin_user_adjust:{u.id}"),
                InlineKeyboardButton(text="📨", callback_data=f"admin_user_message:{u.id}"),
                InlineKeyboardButton(
                    text="🚫" if not u.bloqueado else "🔓",
                    callback_data=f"admin_user_toggle:{u.id}"
                ),
            ])
        texto = "👥 Últimos usuários:\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_users")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# BUSCAR USUÁRIO POR ID
# ==============================================
@router.callback_query(F.data == "admin_user_search")
@admin_only
async def admin_user_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserActionForm.waiting_user_id)
    await callback.message.answer("Digite o ID do Telegram do usuário:")
    await callback.answer()


@router.message(UserActionForm.waiting_user_id)
@admin_only
async def user_id_recebido(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID inválido. Digite um número.")
        return

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Usuário não encontrado.")
            await state.clear()
            return

        # Contagem de compras
        result = await session.execute(
            select(func.count(Venda.id)).where(Venda.user_id == user_id, Venda.status == "pago")
        )
        total_compras = result.scalar() or 0

        texto = (
            f"👤 Usuário #{user.id}\n"
            f"Nome: {user.first_name or 'N/A'} {user.last_name or ''}\n"
            f"Username: @{user.username or 'N/A'}\n"
            f"Saldo: R$ {float(user.saldo):.2f}\n"
            f"Total gasto: R$ {float(user.total_gasto):.2f}\n"
            f"Total recargas: R$ {float(user.total_recargas):.2f}\n"
            f"Total gifts: R$ {float(user.total_gifts):.2f}\n"
            f"Compras realizadas: {total_compras}\n"
            f"Bloqueado: {'Sim' if user.bloqueado else 'Não'}\n"
            f"Cadastro: {user.data_cadastro.strftime('%d/%m/%Y %H:%M')}"
        )

        botoes = [
            [InlineKeyboardButton(text="💰 Ajustar Saldo", callback_data=f"admin_user_adjust:{user.id}")],
            [InlineKeyboardButton(text="📨 Enviar Mensagem", callback_data=f"admin_user_message:{user.id}")],
            [InlineKeyboardButton(
                text="🔓 Desbloquear" if user.bloqueado else "🚫 Bloquear",
                callback_data=f"admin_user_toggle:{user.id}"
            )],
            [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_users")],
        ]
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

        await message.answer(texto, reply_markup=teclado)

    await state.clear()


# ==============================================
# AJUSTAR SALDO DO USUÁRIO
# ==============================================
@router.callback_query(F.data.startswith("admin_user_adjust:"))
@admin_only
async def admin_user_adjust(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await state.set_state(UserActionForm.waiting_adjust_value)
    await callback.message.answer(
        f"Digite o valor para ajustar o saldo do usuário #{user_id}.\n"
        "Use positivo para crédito e negativo para débito.\n"
        "Exemplo: 50.00 ou -10.00"
    )
    await callback.answer()


@router.message(UserActionForm.waiting_adjust_value)
@admin_only
async def adjust_value_received(message: Message, state: FSMContext):
    try:
        valor = Decimal(message.text.replace(",", "."))
    except (ValueError, InvalidOperation):
        await message.answer("Valor inválido.")
        return

    await state.update_data(valor=valor)
    await state.set_state(UserActionForm.waiting_adjust_reason)
    await message.answer("Digite o motivo do ajuste (obrigatório para auditoria):")


@router.message(UserActionForm.waiting_adjust_reason)
@admin_only
async def adjust_reason_received(message: Message, state: FSMContext):
    motivo = message.text.strip()
    if not motivo:
        await message.answer("Motivo obrigatório.")
        return

    dados = await state.get_data()
    user_id = dados["user_id"]
    valor = dados["valor"]

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Usuário não encontrado.")
            await state.clear()
            return

        user.saldo += valor
        # Log
        log = Log(
            user_id=message.from_user.id,
            acao="ajuste_saldo",
            detalhes={"usuario_id": user_id, "valor": float(valor), "motivo": motivo}
        )
        session.add(log)
        await session.commit()

        novo_saldo = float(user.saldo)

    await message.answer(
        f"✅ Saldo ajustado!\n"
        f"Usuário: #{user_id}\n"
        f"Valor: R$ {float(valor):.2f}\n"
        f"Novo saldo: R$ {novo_saldo:.2f}\n"
        f"Motivo: {motivo}"
    )
    await state.clear()


# ==============================================
# ENVIAR MENSAGEM DIRETA AO USUÁRIO
# ==============================================
@router.callback_query(F.data.startswith("admin_user_message:"))
@admin_only
async def admin_user_message(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await state.set_state(UserActionForm.waiting_message_text)
    await callback.message.answer(
        f"Digite a mensagem que deseja enviar ao usuário #{user_id}:"
    )
    await callback.answer()


@router.message(UserActionForm.waiting_message_text)
@admin_only
async def user_message_text(message: Message, state: FSMContext):
    texto = message.text.strip()
    if not texto:
        await message.answer("Mensagem vazia.")
        return

    dados = await state.get_data()
    user_id = dados["user_id"]

    # Envia a mensagem para o usuário
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=texto
        )
        await message.answer(f"✅ Mensagem enviada para o usuário #{user_id}.")
    except Exception as e:
        await message.answer(f"❌ Erro ao enviar mensagem: {e}")

    await state.clear()


# ==============================================
# BLOQUEAR/DESBLOQUEAR USUÁRIO
# ==============================================
@router.callback_query(F.data.startswith("admin_user_toggle:"))
@admin_only
async def admin_user_toggle(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("Usuário não encontrado.", show_alert=True)
            return

        user.bloqueado = not user.bloqueado
        await session.commit()

        status = "bloqueado" if user.bloqueado else "desbloqueado"
        # Log
        log = Log(
            user_id=callback.from_user.id,
            acao="status_usuario",
            detalhes={"usuario_id": user_id, "status": status}
        )
        session.add(log)
        await session.commit()

    await callback.answer(f"Usuário {status}!", show_alert=True)
    await admin_user_list(callback)


# ==============================================
# VER USUÁRIO (DETALHES COMPLETOS)
# ==============================================
@router.callback_query(F.data.startswith("admin_user_view:"))
@admin_only
async def admin_user_view(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("Usuário não encontrado.", show_alert=True)
            return

        result = await session.execute(
            select(func.count(Venda.id)).where(Venda.user_id == user_id, Venda.status == "pago")
        )
        total_compras = result.scalar() or 0

        texto = (
            f"👤 Detalhes do Usuário #{user.id}\n\n"
            f"Telegram ID: {user.id}\n"
            f"Nome: {user.first_name or 'N/A'} {user.last_name or ''}\n"
            f"Username: @{user.username or 'N/A'}\n"
            f"Saldo: R$ {float(user.saldo):.2f}\n"
            f"Total gasto: R$ {float(user.total_gasto):.2f}\n"
            f"Total recargas: R$ {float(user.total_recargas):.2f}\n"
            f"Total gifts: R$ {float(user.total_gifts):.2f}\n"
            f"Compras realizadas: {total_compras}\n"
            f"Indicado por: {user.indicado_por or 'N/A'}\n"
            f"Bloqueado: {'Sim' if user.bloqueado else 'Não'}\n"
            f"Cadastro: {user.data_cadastro.strftime('%d/%m/%Y %H:%M')}"
        )

        botoes = [
            [InlineKeyboardButton(text="💰 Ajustar Saldo", callback_data=f"admin_user_adjust:{user.id}")],
            [InlineKeyboardButton(text="📨 Enviar Mensagem", callback_data=f"admin_user_message:{user.id}")],
            [InlineKeyboardButton(
                text="🔓 Desbloquear" if user.bloqueado else "🚫 Bloquear",
                callback_data=f"admin_user_toggle:{user.id}"
            )],
            [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_users")],
        ]
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()
