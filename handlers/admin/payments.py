# ==============================================
# LARIZINHA STORE - HANDLER ADMIN PAGAMENTOS
# ==============================================

import logging
from datetime import datetime
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import PagamentoPix, User, Log
from keyboards.admin import admin_payments_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA FORÇAR VERIFICAÇÃO DE PAGAMENTO
# ==============================================
class PaymentCheckForm(StatesGroup):
    waiting_payment_id = State()


# ==============================================
# MENU PRINCIPAL DE PAGAMENTOS
# ==============================================
@router.callback_query(F.data == "admin_payments")
@admin_only
async def admin_payments_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💳 Pagamentos\n\nEscolha uma opção:",
        reply_markup=admin_payments_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR PAGAMENTOS PENDENTES
# ==============================================
@router.callback_query(F.data == "admin_payment_pending")
@admin_only
async def admin_payment_pending(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(PagamentoPix)
            .where(PagamentoPix.status == "pendente")
            .order_by(PagamentoPix.data_criacao.desc())
            .limit(20)
        )
        pagamentos = result.scalars().all()

    if not pagamentos:
        texto = "Não há pagamentos pendentes."
        teclado = admin_payments_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for p in pagamentos:
            linhas.append(
                f"#{p.id} | User {p.user_id} | R$ {float(p.valor):.2f} | "
                f"Tipo: {p.tipo} | Expira: {p.data_expiracao.strftime('%d/%m/%Y %H:%M')}"
            )
            botoes.append([
                InlineKeyboardButton(text=f"👁 #{p.id}", callback_data=f"admin_payment_view:{p.id}"),
                InlineKeyboardButton(text="✅ Forçar", callback_data=f"admin_payment_force:{p.id}"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data=f"admin_payment_cancel:{p.id}"),
            ])
        texto = "💳 Pagamentos Pendentes:\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_payments")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# LISTAR PAGAMENTOS APROVADOS
# ==============================================
@router.callback_query(F.data == "admin_payment_approved")
@admin_only
async def admin_payment_approved(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(PagamentoPix)
            .where(PagamentoPix.status == "pago")
            .order_by(PagamentoPix.data_pagamento.desc())
            .limit(20)
        )
        pagamentos = result.scalars().all()

    if not pagamentos:
        texto = "Não há pagamentos aprovados."
        teclado = admin_payments_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for p in pagamentos:
            linhas.append(
                f"#{p.id} | User {p.user_id} | R$ {float(p.valor):.2f} | "
                f"Pago em: {p.data_pagamento.strftime('%d/%m/%Y %H:%M') if p.data_pagamento else 'N/A'}"
            )
            botoes.append([
                InlineKeyboardButton(text=f"👁 #{p.id}", callback_data=f"admin_payment_view:{p.id}"),
            ])
        texto = "✅ Pagamentos Aprovados:\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_payments")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# VER DETALHES DO PAGAMENTO
# ==============================================
@router.callback_query(F.data.startswith("admin_payment_view:"))
@admin_only
async def admin_payment_view(callback: CallbackQuery):
    payment_id = callback.data.split(":")[1]

    async with async_session() as session:
        pagamento = await session.get(PagamentoPix, payment_id)
        if not pagamento:
            await callback.answer("Pagamento não encontrado.", show_alert=True)
            return

        texto = (
            f"💳 Pagamento #{pagamento.id}\n\n"
            f"Usuário: {pagamento.user_id}\n"
            f"Tipo: {pagamento.tipo}\n"
            f"Valor: R$ {float(pagamento.valor):.2f}\n"
            f"Bônus: R$ {float(pagamento.bonus):.2f}\n"
            f"Status: {pagamento.status}\n"
            f"TxID: {pagamento.txid or 'N/A'}\n"
            f"Criado em: {pagamento.data_criacao.strftime('%d/%m/%Y %H:%M')}\n"
            f"Expira em: {pagamento.data_expiracao.strftime('%d/%m/%Y %H:%M') if pagamento.data_expiracao else 'N/A'}\n"
            f"Pago em: {pagamento.data_pagamento.strftime('%d/%m/%Y %H:%M') if pagamento.data_pagamento else 'N/A'}\n"
            f"Referência: {pagamento.referencia or 'N/A'}\n\n"
            f"Código PIX:\n<code>{pagamento.codigo_pix or 'N/A'}</code>"
        )

        botoes = []
        if pagamento.status == "pendente":
            botoes.append([
                InlineKeyboardButton(text="✅ Forçar Aprovação", callback_data=f"admin_payment_force:{pagamento.id}"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data=f"admin_payment_cancel:{pagamento.id}"),
            ])
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_payments")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# FORÇAR APROVAÇÃO DE PAGAMENTO
# ==============================================
@router.callback_query(F.data.startswith("admin_payment_force:"))
@admin_only
async def admin_payment_force(callback: CallbackQuery):
    payment_id = callback.data.split(":")[1]

    async with async_session() as session:
        pagamento = await session.get(PagamentoPix, payment_id)
        if not pagamento:
            await callback.answer("Pagamento não encontrado.", show_alert=True)
            return

        if pagamento.status != "pendente":
            await callback.answer("Pagamento não está pendente.", show_alert=True)
            return

        # Marca como pago
        pagamento.status = "pago"
        pagamento.data_pagamento = datetime.now()

        # Credita saldo se for recarga (ou compra? Depende do tipo)
        user = await session.get(User, pagamento.user_id)
        if user:
            if pagamento.tipo == "recarga":
                user.saldo += pagamento.valor + pagamento.bonus
                user.total_recargas += pagamento.valor
            # Se for compra, a entrega de produto seria tratada em serviço separado
            # Nesse caso simplificamos apenas creditando se for recarga

        # Log
        log = Log(
            user_id=callback.from_user.id,
            acao="pagamento_forcado",
            detalhes={"payment_id": str(pagamento.id), "status": "pago"}
        )
        session.add(log)
        await session.commit()

    await callback.answer("Pagamento aprovado manualmente!", show_alert=True)
    await admin_payment_pending(callback)


# ==============================================
# CANCELAR PAGAMENTO
# ==============================================
@router.callback_query(F.data.startswith("admin_payment_cancel:"))
@admin_only
async def admin_payment_cancel(callback: CallbackQuery):
    payment_id = callback.data.split(":")[1]

    async with async_session() as session:
        pagamento = await session.get(PagamentoPix, payment_id)
        if not pagamento:
            await callback.answer("Pagamento não encontrado.", show_alert=True)
            return

        if pagamento.status != "pendente":
            await callback.answer("Pagamento não está pendente.", show_alert=True)
            return

        pagamento.status = "cancelado"

        # Log
        log = Log(
            user_id=callback.from_user.id,
            acao="pagamento_cancelado",
            detalhes={"payment_id": str(pagamento.id)}
        )
        session.add(log)
        await session.commit()

    await callback.answer("Pagamento cancelado.", show_alert=True)
    await admin_payment_pending(callback)
