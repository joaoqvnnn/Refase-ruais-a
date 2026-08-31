# ==============================================
# LARIZINHA STORE - HANDLER RANKINGS
# ==============================================

import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc

from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.connection import async_session
from database.models import User, Produto, Venda, PagamentoPix
from keyboards.client import rankings_keyboard, back_to_main_keyboard
from texts.client import get_message

logger = logging.getLogger(__name__)
router = Router()


# Funções auxiliares de formatação

def _formatar_lista_top(itens: list, tipo: str) -> str:
    """
    Formata uma lista de itens de ranking com medalhas.
    """
    if not itens:
        return "Nenhum dado disponível."

    medalhas = ["🥇", "🥈", "🥉"]
    linhas = []
    for i, item in enumerate(itens, start=1):
        medalha = medalhas[i-1] if i <= 3 else f"{i}°"
        if tipo == "produto":
            linhas.append(f"{medalha} {item['nome']} - Com {item['total']} pedidos")
        elif tipo == "recarga":
            linhas.append(f"{medalha} {item['nome']} - R$ {item['total']:.2f}")
        elif tipo == "saldo":
            linhas.append(f"{medalha} {item['nome']} - R$ {item['total']:.2f}")
        elif tipo == "compra":
            linhas.append(f"{medalha} {item['nome']} - {item['total']} compras")
    return "\n".join(linhas)


def _verificar_usuario_no_ranking(user_id: int, itens: list, campo_id: str = "user_id") -> str:
    """
    Verifica se o usuário está no ranking e retorna mensagem apropriada.
    """
    for i, item in enumerate(itens, start=1):
        if item.get(campo_id) == user_id:
            return f"🏅 Você está na posição {i}°!"
    return None  # retorna None se não estiver


# Rankings de serviços mais vendidos

@router.callback_query(F.data == "menu_rankings")
async def menu_rankings(callback: CallbackQuery):
    await show_rankings(callback, "servicos")


@router.callback_query(F.data.startswith("ranking_"))
async def ranking_selecionado(callback: CallbackQuery):
    tipo = callback.data.replace("ranking_", "")
    await show_rankings(callback, tipo)


async def show_rankings(callback: CallbackQuery, tipo: str = "servicos"):
    """
    Exibe o ranking conforme o tipo selecionado.
    """
    user_id = callback.from_user.id
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year

    async with async_session() as session:
        if tipo == "servicos":
            # Produtos mais vendidos do mês
            result = await session.execute(
                select(Produto.nome, Produto.emoji, func.count(Venda.id).label("total_vendas"))
                .join(Venda, Venda.produto_id == Produto.id)
                .where(
                    Venda.status == "pago",
                    func.extract("month", Venda.data_compra) == mes_atual,
                    func.extract("year", Venda.data_compra) == ano_atual,
                )
                .group_by(Produto.id)
                .order_by(desc("total_vendas"))
                .limit(10)
            )
            linhas = result.all()
            itens = [{"nome": f"{emoji} {nome}", "total": total} for nome, emoji, total in linhas]
            mensagem_usuario = ""
            # Verificar se o usuário está? Não se aplica a produtos.

        elif tipo == "recargas":
            # Usuários que mais recarregaram no mês
            result = await session.execute(
                select(User.first_name, User.username, func.sum(PagamentoPix.valor).label("total_recargas"))
                .join(PagamentoPix, PagamentoPix.user_id == User.id)
                .where(
                    PagamentoPix.tipo == "recarga",
                    PagamentoPix.status == "pago",
                    func.extract("month", PagamentoPix.data_pagamento) == mes_atual,
                    func.extract("year", PagamentoPix.data_pagamento) == ano_atual,
                )
                .group_by(User.id)
                .order_by(desc("total_recargas"))
                .limit(10)
            )
            linhas = result.all()
            itens = [{"user_id": None, "nome": nome or username or "Usuário", "total": float(total or 0)} for nome, username, total in linhas]
            # Preencher user_id para verificação
            # Necessário refazer consulta com id
            # Simplificação: assumir que não há verificação para este tipo agora
            mensagem_usuario = ""

        elif tipo == "saldo":
            # Usuários com mais saldo na carteira
            result = await session.execute(
                select(User.id, User.first_name, User.username, User.saldo)
                .order_by(desc(User.saldo))
                .limit(10)
            )
            linhas = result.all()
            itens = [{"user_id": uid, "nome": nome or username or "Usuário", "total": float(saldo or 0)} for uid, nome, username, saldo in linhas]
            mensagem_usuario = ""
            # Verificar se o usuário está no ranking
            pos = None
            for i, item in enumerate(itens):
                if item.get("user_id") == user_id:
                    pos = i + 1
                    break
            if pos:
                mensagem_usuario = f"🏅 Você está na posição {pos}°!"
            else:
                # Verificar quanto falta
                if itens:
                    ultimo = itens[-1]["total"]
                    # buscar saldo do usuário
                    user = await session.get(User, user_id)
                    if user:
                        falta = ultimo - float(user.saldo)
                        if falta > 0:
                            mensagem_usuario = f"💡 Você ainda não está no ranking. Adicione mais R$ {falta:.2f} para aparecer!"
                        else:
                            mensagem_usuario = "💡 Você está no ranking!"

        elif tipo == "compras":
            # Usuários que mais compraram no mês
            result = await session.execute(
                select(User.id, User.first_name, User.username, func.count(Venda.id).label("total_compras"))
                .join(Venda, Venda.user_id == User.id)
                .where(
                    Venda.status == "pago",
                    func.extract("month", Venda.data_compra) == mes_atual,
                    func.extract("year", Venda.data_compra) == ano_atual,
                )
                .group_by(User.id)
                .order_by(desc("total_compras"))
                .limit(10)
            )
            linhas = result.all()
            itens = [{"user_id": uid, "nome": nome or username or "Usuário", "total": int(total or 0)} for uid, nome, username, total in linhas]
            mensagem_usuario = ""
            pos = None
            for i, item in enumerate(itens):
                if item.get("user_id") == user_id:
                    pos = i + 1
                    break
            if pos:
                mensagem_usuario = f"🏅 Você está na posição {pos}°!"
            else:
                user = await session.get(User, user_id)
                if user:
                    # Buscar total de compras do usuário no mês
                    result_user = await session.execute(
                        select(func.count(Venda.id))
                        .where(
                            Venda.user_id == user_id,
                            Venda.status == "pago",
                            func.extract("month", Venda.data_compra) == mes_atual,
                            func.extract("year", Venda.data_compra) == ano_atual,
                        )
                    )
                    total_user = result_user.scalar() or 0
                    if itens:
                        falta = itens[-1]["total"] - total_user
                        if falta > 0:
                            mensagem_usuario = f"💡 Você ainda não está no ranking. Faça mais {falta} compras para aparecer!"
                        else:
                            mensagem_usuario = "💡 Você está no ranking!"

        else:
            # Tipo inválido
            await callback.answer("Tipo de ranking inválido.", show_alert=True)
            return

    # Monta a lista formatada
    lista_formatada = _formatar_lista_top(itens, tipo)

    # Título conforme tipo
    titulos = {
        "servicos": "🏆 Ranking dos serviços mais vendidos (deste mês)",
        "recargas": "🏆 Ranking dos usuários que mais recarregaram (deste mês)",
        "saldo": "🏆 Ranking dos usuários com mais saldo no bot",
        "compras": "🏆 Ranking dos usuários que mais compraram (deste mês)",
    }
    titulo = titulos.get(tipo, "🏆 Ranking")

    texto = f"{titulo}\n\n{lista_formatada}"

    if mensagem_usuario:
        texto += f"\n\n{mensagem_usuario}"

    await callback.message.edit_text(
        texto,
        reply_markup=rankings_keyboard(tipo),
    )
    await callback.answer()
