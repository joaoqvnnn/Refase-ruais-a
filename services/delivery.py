# ==============================================
# LARIZINHA STORE - SERVIÇO DE ENTREGA AUTOMÁTICA
# ==============================================

import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session
from database.models import Venda, Produto, EstoqueItem, User
from utils.helpers import format_money

logger = logging.getLogger(__name__)


async def selecionar_itens_estoque(session: AsyncSession, produto_id: int, quantidade: int) -> list[EstoqueItem] | None:
    """
    Seleciona 'quantidade' itens não vendidos de um produto e os marca como vendidos.
    Retorna lista com os itens ou None se estoque insuficiente.
    """
    result = await session.execute(
        select(EstoqueItem)
        .where(EstoqueItem.produto_id == produto_id, EstoqueItem.vendido == False)
        .limit(quantidade)
    )
    itens = result.scalars().all()

    if len(itens) < quantidade:
        return None

    for item in itens:
        item.vendido = True

    return itens


async def formatar_entrega(venda: Venda, produto: Produto, itens: list[EstoqueItem]) -> str:
    """
    Monta a mensagem de entrega usando o template do produto e os itens vendidos.
    """
    if produto.mensagem_entrega:
        template = produto.mensagem_entrega
    else:
        template = "{conteudo}"

    # Se houver apenas um item, faz substituição simples
    conteudos = [item.conteudo for item in itens]

    if len(conteudos) == 1:
        conteudo = conteudos[0]
        # Suporta variáveis comuns no template
        mensagem = template.format(
            conteudo=conteudo,
            email=conteudo.split(":")[0] if ":" in conteudo else conteudo,
            senha=conteudo.split(":")[1] if ":" in conteudo and len(conteudo.split(":")) > 1 else "",
            produto=produto.nome,
            valor=format_money(venda.valor_total),
            data=venda.data_compra.strftime("%d/%m/%Y"),
            hora=venda.data_compra.strftime("%H:%M"),
            vencimento=venda.vencimento.strftime("%d/%m/%Y") if venda.vencimento else "N/A",
            garantia=produto.garantia_dias,
        )
    else:
        # Para múltiplos itens, junta os conteúdos
        lista_conteudos = "\n\n".join(conteudos)
        mensagem = template.replace("{conteudo}", lista_conteudos)
        mensagem = mensagem.replace("{produto}", produto.nome)
        mensagem = mensagem.replace("{valor}", format_money(venda.valor_total))
        mensagem = mensagem.replace("{data}", venda.data_compra.strftime("%d/%m/%Y"))
        mensagem = mensagem.replace("{hora}", venda.data_compra.strftime("%H:%M"))
        mensagem = mensagem.replace(
            "{vencimento}",
            venda.vencimento.strftime("%d/%m/%Y") if venda.vencimento else "N/A"
        )
        mensagem = mensagem.replace("{garantia}", str(produto.garantia_dias))

    return mensagem


async def enviar_entrega_telegram(bot, user_id: int, texto: str) -> bool:
    """
    Envia a mensagem de entrega via Telegram.
    Retorna True se enviou com sucesso.
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=texto,
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar entrega para {user_id}: {e}")
        return False


async def processar_entrega(venda_id, bot=None) -> bool:
    """
    Processa a entrega de uma venda já aprovada.
    Seleciona itens do estoque, atualiza a venda e envia a mensagem.
    """
    import uuid
    from database.models import Venda, Produto

    async with async_session() as session:
        venda = await session.get(Venda, uuid.UUID(str(venda_id)))
        if not venda:
            logger.error(f"Venda {venda_id} não encontrada.")
            return False

        produto = await session.get(Produto, venda.produto_id)
        if not produto:
            logger.error(f"Produto {venda.produto_id} não encontrado.")
            return False

        # Seleciona itens
        itens = await selecionar_itens_estoque(session, venda.produto_id, venda.quantidade)
        if not itens:
            logger.error(f"Estoque insuficiente para venda {venda_id}.")
            return False

        # Conteúdo dos itens
        conteudos = [item.conteudo for item in itens]

        # Atualiza venda
        venda.itens_entregues = conteudos
        venda.status = "pago"
        venda.data_compra = datetime.now()

        # Diminui estoque e incrementa vendidos
        produto.estoque -= venda.quantidade
        produto.vendidos += venda.quantidade

        await session.commit()

        # Monta texto de entrega
        texto = await formatar_entrega(venda, produto, itens)

        # Envia via Telegram se bot fornecido
        if bot:
            user = await session.get(User, venda.user_id)
            if user:
                enviado = await enviar_entrega_telegram(bot, user.id, texto)
                if not enviado:
                    logger.warning(f"Falha ao enviar Telegram para {user.id}")

        logger.info(f"Entrega processada para venda {venda_id}")
        return True
