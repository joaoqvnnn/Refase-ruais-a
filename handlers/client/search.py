# ==============================================
# LARIZINHA STORE - HANDLER PESQUISA INLINE
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import select
from database.connection import async_session
from database.models import Produto
from texts.client import get_message

logger = logging.getLogger(__name__)
router = Router()


async def pesquisar_servico(termo: str) -> list[Produto]:
    """
    Busca produtos ativos cujo nome ou descrição contenha o termo.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Produto)
            .where(
                Produto.ativo == True,
                (Produto.nome.ilike(f"%{termo}%")) | (Produto.descricao.ilike(f"%{termo}%"))
            )
            .limit(10)
        )
        return result.scalars().all()


@router.callback_query(F.data.startswith("pesquisar_servico:"))
async def pesquisar_servico_callback(callback: CallbackQuery):
    """
    Callback para iniciar uma pesquisa inline (botão do menu).
    """
    # O botão de pesquisa no menu usa switch_inline_query_current_chat,
    # então este handler é acionado apenas se houver callback personalizado.
    # Vamos apenas orientar o usuário a usar a pesquisa inline.
    await callback.answer(
        "🔍 Use a pesquisa inline: digite @larizinhastorebot + termo",
        show_alert=True,
    )


# Tratamento da inline query (quando o usuário digita no campo de busca do Telegram)
@router.inline_query()
async def inline_query_handler(inline_query):
    """
    Responde à pesquisa inline do usuário com produtos correspondentes.
    """
    termo = inline_query.query.strip()
    if not termo:
        # Sem termo, retorna vazio ou itens em destaque
        return

    produtos = await pesquisar_servico(termo)

    if not produtos:
        # Nenhum resultado: enviamos um item informativo
        result = InlineQueryResultArticle(
            id="sem_resultados",
            title="Nenhum serviço encontrado",
            description="Tente outro termo de busca",
            input_message_content=InputTextMessageContent(
                message_text="❌ Nenhum serviço encontrado para sua pesquisa."
            ),
        )
        await inline_query.answer([result], cache_time=0)
        return

    # Monta resultados para o menu inline
    results = []
    for produto in produtos:
        resultado = InlineQueryResultArticle(
            id=str(produto.id),
            title=f"{produto.emoji} {produto.nome}",
            description=f"R$ {float(produto.preco):.2f} - {produto.descricao[:50]}",
            input_message_content=InputTextMessageContent(
                message_text=await get_message(
                    "pesquisa",
                    nome_produto=produto.nome,
                    preco=f"{float(produto.preco):.2f}",
                    descricao=produto.descricao or "Sem descrição.",
                )
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Comprar", callback_data=f"comprar:{produto.id}")]
            ])
        )
        results.append(resultado)

    await inline_query.answer(results, cache_time=0)
