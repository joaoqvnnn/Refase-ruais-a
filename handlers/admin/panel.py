# ==============================================
# LARIZINHA STORE - PAINEL ADMINISTRATIVO (MENU PRINCIPAL)
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards.admin import admin_menu_keyboard
from utils.decorators import admin_only

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("admin"))
@admin_only
async def cmd_admin(message: Message):
    """
    Comando /admin para abrir o painel administrativo.
    """
    await message.answer(
        "🔧 PAINEL ADMINISTRATIVO\n\n"
        "Selecione uma opção abaixo:",
        reply_markup=admin_menu_keyboard()
    )


@router.message(Command("painel"))
@admin_only
async def cmd_painel(message: Message):
    """
    Comando /painel como atalho para o mesmo painel.
    """
    await cmd_admin(message)


@router.callback_query(F.data == "admin_panel")
@admin_only
async def admin_panel_callback(callback: CallbackQuery):
    """
    Callback para retornar ao menu principal do painel.
    """
    await callback.message.edit_text(
        "🔧 PAINEL ADMINISTRATIVO\n\n"
        "Selecione uma opção abaixo:",
        reply_markup=admin_menu_keyboard()
    )
    await callback.answer()
