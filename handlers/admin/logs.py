# ==============================================
# LARIZINHA STORE - HANDLER ADMIN LOGS
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, desc, func
from database.connection import async_session
from database.models import Log
from keyboards.admin import admin_logs_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only
from utils.validators import validar_id_telegram

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA FILTRAR LOGS POR USUÁRIO
# ==============================================
class LogFilterForm(StatesGroup):
    waiting_user_id = State()


# ==============================================
# MENU PRINCIPAL DE LOGS
# ==============================================
@router.callback_query(F.data == "admin_logs")
@admin_only
async def admin_logs_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Logs do Sistema\n\n"
        "Escolha uma opção:",
        reply_markup=admin_logs_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR LOGS RECENTES
# ==============================================
@router.callback_query(F.data == "admin_log_view")
@admin_only
async def admin_log_view(callback: CallbackQuery, page: int = 0):
    """
    Exibe os logs mais recentes, com paginação simples.
    """
    itens_por_pagina = 10

    async with async_session() as session:
        # Consulta total de logs
        total_logs = (await session.execute(select(func.count(Log.id)))).scalar() or 0

        # Busca logs da página atual
        result = await session.execute(
            select(Log)
            .order_by(desc(Log.data))
            .offset(page * itens_por_pagina)
            .limit(itens_por_pagina)
        )
        logs = result.scalars().all()

    if not logs:
        texto = "Nenhum log registrado."
        teclado = admin_logs_menu_keyboard()
    else:
        linhas = []
        for log in logs:
            detalhes = log.detalhes or {}
            linhas.append(
                f"#{log.id} | {log.data.strftime('%d/%m/%Y %H:%M')} | "
                f"User: {log.user_id or 'N/A'} | {log.acao}"
            )
        texto = "📋 Logs Recentes:\n\n" + "\n".join(linhas)

        # Botões de paginação e filtros
        botoes = []
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_log_page:{page-1}"))
        if (page + 1) * itens_por_pagina < total_logs:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_log_page:{page+1}"))
        if nav:
            botoes.append(nav)

        botoes.append([
            InlineKeyboardButton(text="🔍 Filtrar por Usuário", callback_data="admin_log_filter_user")
        ])
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_logs")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_log_page:"))
@admin_only
async def admin_log_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await admin_log_view(callback, page)


# ==============================================
# FILTRAR LOGS POR USUÁRIO (FSM)
# ==============================================
@router.callback_query(F.data == "admin_log_filter_user")
@admin_only
async def admin_log_filter_user_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LogFilterForm.waiting_user_id)
    await callback.message.answer("Digite o ID do Telegram do usuário para filtrar os logs:")
    await callback.answer()


@router.message(LogFilterForm.waiting_user_id)
@admin_only
async def admin_log_filter_user_received(message: Message, state: FSMContext):
    user_id_str = message.text.strip()
    if not validar_id_telegram(user_id_str):
        await message.answer("ID inválido. Digite um número inteiro positivo.")
        return

    user_id = int(user_id_str)

    async with async_session() as session:
        result = await session.execute(
            select(Log)
            .where(Log.user_id == user_id)
            .order_by(desc(Log.data))
            .limit(20)
        )
        logs = result.scalars().all()

    if not logs:
        texto = f"Nenhum log encontrado para o usuário #{user_id}."
    else:
        linhas = []
        for log in logs:
            detalhes = log.detalhes or {}
            linhas.append(
                f"#{log.id} | {log.data.strftime('%d/%m/%Y %H:%M')} | {log.acao}"
            )
        texto = f"📋 Logs do usuário #{user_id}:\n\n" + "\n".join(linhas)

    await message.answer(texto, reply_markup=admin_back_keyboard("admin_logs"))
    await state.clear()
