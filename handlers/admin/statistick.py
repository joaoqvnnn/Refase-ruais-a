# ==============================================
# LARIZINHA STORE - HANDLER ADMIN ESTATÍSTICAS
# ==============================================

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import select, func, extract
from database.connection import async_session
from database.models import User, Venda, PagamentoPix, Produto
from keyboards.admin import admin_back_keyboard
from utils.decorators import admin_only

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# MENU DE ESTATÍSTICAS
# ==============================================
@router.callback_query(F.data == "admin_statistics")
@admin_only
async def admin_statistics_menu(callback: CallbackQuery):
    botoes = [
        [InlineKeyboardButton(text="📊 Resumo Geral", callback_data="admin_stats_general")],
        [InlineKeyboardButton(text="💰 Vendas de Hoje", callback_data="admin_stats_today")],
        [InlineKeyboardButton(text="📅 Vendas do Mês", callback_data="admin_stats_month")],
        [InlineKeyboardButton(text="👥 Usuários", callback_data="admin_stats_users")],
        [InlineKeyboardButton(text="🏆 Produtos Mais Vendidos", callback_data="admin_stats_products")],
        [InlineKeyboardButton(text="💳 Recargas do Mês", callback_data="admin_stats_recharges")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(
        "📊 Estatísticas\n\nSelecione uma opção:",
        reply_markup=teclado
    )
    await callback.answer()


# ==============================================
# RESUMO GERAL
# ==============================================
@router.callback_query(F.data == "admin_stats_general")
@admin_only
async def admin_stats_general(callback: CallbackQuery):
    async with async_session() as session:
        # Total de usuários
        total_usuarios = (await session.execute(select(func.count(User.id)))).scalar() or 0

        # Total de vendas (todas)
        total_vendas = (await session.execute(
            select(func.count(Venda.id)).where(Venda.status == "pago")
        )).scalar() or 0

        # Faturamento total
        faturamento_total = (await session.execute(
            select(func.coalesce(func.sum(Venda.valor_total), 0)).where(Venda.status == "pago")
        )).scalar() or 0

        # Total de recargas
        total_recargas = (await session.execute(
            select(func.coalesce(func.sum(PagamentoPix.valor), 0)).where(
                PagamentoPix.tipo == "recarga",
                PagamentoPix.status == "pago"
            )
        )).scalar() or 0

        # Produtos ativos
        produtos_ativos = (await session.execute(
            select(func.count(Produto.id)).where(Produto.ativo == True)
        )).scalar() or 0

    texto = (
        "📊 RESUMO GERAL\n\n"
        f"👥 Usuários: {total_usuarios}\n"
        f"🛒 Vendas concluídas: {total_vendas}\n"
        f"💰 Faturamento total: R$ {float(faturamento_total):.2f}\n"
        f"💳 Total recarregado: R$ {float(total_recargas):.2f}\n"
        f"📦 Produtos ativos: {produtos_ativos}"
    )

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_statistics")
    )
    await callback.answer()


# ==============================================
# VENDAS DE HOJE
# ==============================================
@router.callback_query(F.data == "admin_stats_today")
@admin_only
async def admin_stats_today(callback: CallbackQuery):
    hoje = datetime.now().date()
    inicio_dia = datetime.combine(hoje, datetime.min.time())

    async with async_session() as session:
        total_vendas = (await session.execute(
            select(func.count(Venda.id)).where(
                Venda.status == "pago",
                Venda.data_compra >= inicio_dia
            )
        )).scalar() or 0

        faturamento = (await session.execute(
            select(func.coalesce(func.sum(Venda.valor_total), 0)).where(
                Venda.status == "pago",
                Venda.data_compra >= inicio_dia
            )
        )).scalar() or 0

    texto = (
        "💰 VENDAS DE HOJE\n\n"
        f"Pedidos: {total_vendas}\n"
        f"Faturamento: R$ {float(faturamento):.2f}"
    )

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_statistics")
    )
    await callback.answer()


# ==============================================
# VENDAS DO MÊS
# ==============================================
@router.callback_query(F.data == "admin_stats_month")
@admin_only
async def admin_stats_month(callback: CallbackQuery):
    agora = datetime.now()
    primeiro_dia = datetime(agora.year, agora.month, 1)

    async with async_session() as session:
        total_vendas = (await session.execute(
            select(func.count(Venda.id)).where(
                Venda.status == "pago",
                Venda.data_compra >= primeiro_dia
            )
        )).scalar() or 0

        faturamento = (await session.execute(
            select(func.coalesce(func.sum(Venda.valor_total), 0)).where(
                Venda.status == "pago",
                Venda.data_compra >= primeiro_dia
            )
        )).scalar() or 0

    texto = (
        "📅 VENDAS DO MÊS\n\n"
        f"Pedidos: {total_vendas}\n"
        f"Faturamento: R$ {float(faturamento):.2f}"
    )

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_statistics")
    )
    await callback.answer()


# ==============================================
# USUÁRIOS
# ==============================================
@router.callback_query(F.data == "admin_stats_users")
@admin_only
async def admin_stats_users(callback: CallbackQuery):
    async with async_session() as session:
        total_usuarios = (await session.execute(select(func.count(User.id)))).scalar() or 0

        # Novos hoje
        hoje = datetime.now().date()
        inicio_dia = datetime.combine(hoje, datetime.min.time())
        novos_hoje = (await session.execute(
            select(func.count(User.id)).where(User.data_cadastro >= inicio_dia)
        )).scalar() or 0

        # Novos no mês
        agora = datetime.now()
        primeiro_dia = datetime(agora.year, agora.month, 1)
        novos_mes = (await session.execute(
            select(func.count(User.id)).where(User.data_cadastro >= primeiro_dia)
        )).scalar() or 0

    texto = (
        "👥 USUÁRIOS\n\n"
        f"Total: {total_usuarios}\n"
        f"Novos hoje: {novos_hoje}\n"
        f"Novos no mês: {novos_mes}"
    )

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_statistics")
    )
    await callback.answer()


# ==============================================
# PRODUTOS MAIS VENDIDOS
# ==============================================
@router.callback_query(F.data == "admin_stats_products")
@admin_only
async def admin_stats_products(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Produto.nome, Produto.emoji, func.count(Venda.id).label("total_vendas"))
            .join(Venda, Venda.produto_id == Produto.id)
            .where(Venda.status == "pago")
            .group_by(Produto.id)
            .order_by(func.count(Venda.id).desc())
            .limit(10)
        )
        produtos = result.all()

    if not produtos:
        texto = "Nenhuma venda registrada."
    else:
        linhas = []
        for nome, emoji, total in produtos:
            linhas.append(f"{emoji or '🛒'} {nome} - {total} vendas")
        texto = "🏆 PRODUTOS MAIS VENDIDOS\n\n" + "\n".join(linhas)

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_statistics")
    )
    await callback.answer()


# ==============================================
# RECARGAS DO MÊS
# ==============================================
@router.callback_query(F.data == "admin_stats_recharges")
@admin_only
async def admin_stats_recharges(callback: CallbackQuery):
    agora = datetime.now()
    primeiro_dia = datetime(agora.year, agora.month, 1)

    async with async_session() as session:
        total_recargas = (await session.execute(
            select(func.coalesce(func.sum(PagamentoPix.valor), 0)).where(
                PagamentoPix.tipo == "recarga",
                PagamentoPix.status == "pago",
                PagamentoPix.data_pagamento >= primeiro_dia
            )
        )).scalar() or 0

        qtd_recargas = (await session.execute(
            select(func.count(PagamentoPix.id)).where(
                PagamentoPix.tipo == "recarga",
                PagamentoPix.status == "pago",
                PagamentoPix.data_pagamento >= primeiro_dia
            )
        )).scalar() or 0

    texto = (
        "💳 RECARGAS DO MÊS\n\n"
        f"Quantidade: {qtd_recargas}\n"
        f"Valor total: R$ {float(total_recargas):.2f}"
    )

    await callback.message.edit_text(
        texto,
        reply_markup=admin_back_keyboard("admin_statistics")
    )
    await callback.answer()
