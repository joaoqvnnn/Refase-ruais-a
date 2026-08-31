# ==============================================
# LARIZINHA STORE - SERVIÇO DE RANKINGS
# ==============================================

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, func, desc

from database.connection import async_session
from database.models import Produto, Venda, User, PagamentoPix

logger = logging.getLogger(__name__)


async def get_ranking_produtos(mes: int = None, ano: int = None, limite: int = 10) -> list[dict]:
    """
    Retorna os produtos mais vendidos do mês/ano especificados.
    Se mes/ano não informados, usa o mês atual.
    """
    agora = datetime.now()
    mes = mes or agora.month
    ano = ano or agora.year

    async with async_session() as session:
        result = await session.execute(
            select(
                Produto.nome,
                Produto.emoji,
                func.count(Venda.id).label("total_vendas")
            )
            .join(Venda, Venda.produto_id == Produto.id)
            .where(
                Venda.status == "pago",
                func.extract("month", Venda.data_compra) == mes,
                func.extract("year", Venda.data_compra) == ano,
            )
            .group_by(Produto.id)
            .order_by(desc("total_vendas"))
            .limit(limite)
        )
        linhas = result.all()

    return [
        {"nome": f"{emoji or '🛒'} {nome}", "total": int(total)}
        for nome, emoji, total in linhas
    ]


async def get_ranking_recargas(mes: int = None, ano: int = None, limite: int = 10) -> list[dict]:
    """
    Retorna os usuários que mais recarregaram no mês/ano.
    """
    agora = datetime.now()
    mes = mes or agora.month
    ano = ano or agora.year

    async with async_session() as session:
        result = await session.execute(
            select(
                User.id,
                User.first_name,
                User.username,
                func.coalesce(func.sum(PagamentoPix.valor), 0).label("total_recarga")
            )
            .join(PagamentoPix, PagamentoPix.user_id == User.id)
            .where(
                PagamentoPix.tipo == "recarga",
                PagamentoPix.status == "pago",
                func.extract("month", PagamentoPix.data_pagamento) == mes,
                func.extract("year", PagamentoPix.data_pagamento) == ano,
            )
            .group_by(User.id)
            .order_by(desc("total_recarga"))
            .limit(limite)
        )
        linhas = result.all()

    return [
        {
            "user_id": uid,
            "nome": nome or username or str(uid),
            "total": float(total),
        }
        for uid, nome, username, total in linhas
    ]


async def get_ranking_saldo(limite: int = 10) -> list[dict]:
    """
    Retorna os usuários com maior saldo em carteira.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User.id, User.first_name, User.username, User.saldo)
            .order_by(desc(User.saldo))
            .limit(limite)
        )
        linhas = result.all()

    return [
        {
            "user_id": uid,
            "nome": nome or username or str(uid),
            "total": float(saldo or 0),
        }
        for uid, nome, username, saldo in linhas
    ]


async def get_ranking_compras(mes: int = None, ano: int = None, limite: int = 10) -> list[dict]:
    """
    Retorna os usuários que mais compraram no mês/ano.
    """
    agora = datetime.now()
    mes = mes or agora.month
    ano = ano or agora.year

    async with async_session() as session:
        result = await session.execute(
            select(
                User.id,
                User.first_name,
                User.username,
                func.count(Venda.id).label("total_compras")
            )
            .join(Venda, Venda.user_id == User.id)
            .where(
                Venda.status == "pago",
                func.extract("month", Venda.data_compra) == mes,
                func.extract("year", Venda.data_compra) == ano,
            )
            .group_by(User.id)
            .order_by(desc("total_compras"))
            .limit(limite)
        )
        linhas = result.all()

    return [
        {
            "user_id": uid,
            "nome": nome or username or str(uid),
            "total": int(total),
        }
        for uid, nome, username, total in linhas
    ]


async def refresh_rankings() -> None:
    """
    Tarefa periódica para atualizar rankings (pode ser usada com Celery).
    Aqui, os rankings são consultados em tempo real, então esta função
    é apenas um placeholder para futuras otimizações com cache.
    """
    logger.info("Refresh de rankings executado (nada a fazer em modo tempo real).")
