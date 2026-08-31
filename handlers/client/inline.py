# ==============================================
# LARIZINHA STORE - HANDLERS DE INLINE QUERY
# ==============================================

import logging
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import select
from database.connection import async_session
from database.models import Produto
from texts.client import get_message

logger = logging.getLogger(__name__)
router = Router()


async def _buscar_produtos(termo: str, limite: int = 10) -> list[Produto]:
    """
    Busca produtos ativos que correspondem ao termo informado.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Produto)
            .where(
                Produto.ativo == True,
                (Produto.nome.ilike(f"%{termo}%")) | (Produto.descricao.ilike(f"%{termo}%"))
            )
            .limit(limite)
        )
        return result.scalars().all()


@router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    """
    Responde à pesquisa inline do usuário.
    O usuário digita @larizinhastorebot + termo e vê resultados.
    """
    termo = inline_query.query.strip()

    if not termo:
        # Sem termo, retorna vazio
        await inline_query.answer([], cache_time=0)
        return

    produtos = await _buscar_produtos(termo)

    if not produtos:
        resultado_vazio = InlineQueryResultArticle(
            id="sem_resultados",
            title="Nenhum serviço encontrado",
            description="Tente outro termo de busca",
            input_message_content=InputTextMessageContent(
                message_text="❌ Nenhum serviço encontrado para sua pesquisa."
            ),
        )
        await inline_query.answer([resultado_vazio], cache_time=0)
        return

    resultados = []
    for produto in produtos:
        texto = get_message(
            "pesquisa",
            nome_produto=produto.nome,
            preco=f"{float(produto.preco):.2f}",
            descricao=produto.descricao or "Sem descrição.",
        )

        resultado = InlineQueryResultArticle(
            id=str(produto.id),
            title=f"{produto.emoji or '🛒'} {produto.nome}",
            description=f"R$ {float(produto.preco):.2f}",
            input_message_content=InputTextMessageContent(message_text=texto),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Comprar", callback_data=f"comprar:{produto.id}")]
            ])
        )
        resultados.append(resultado)

    await inline_query.answer(resultados, cache_time=0)
