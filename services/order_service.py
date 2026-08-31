# ==============================================
# LARIZINHA STORE - SERVIÇO DE PROCESSAMENTO DE PEDIDOS PAGOS VIA PIX
# ==============================================

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session
from database.models import User, Produto, EstoqueItem, Venda, PagamentoPix, Log
from utils.helpers import calcular_vencimento

logger = logging.getLogger(__name__)


async def processar_pagamento_compra(pagamento_id: str) -> bool:
    """
    Processa a entrega de uma compra paga via PIX.
    Deve ser chamado após a confirmação do pagamento (webhook ou verificação manual).
    Retorna True se a entrega foi realizada com sucesso.
    """
    async with async_session() as session:
        pagamento = await session.get(PagamentoPix, uuid.UUID(pagamento_id))
        if not pagamento or pagamento.tipo != "compra":
            logger.warning(f"Pagamento {pagamento_id} não é de compra ou não encontrado.")
            return False

        if pagamento.status != "pago":
            logger.warning(f"Pagamento {pagamento_id} não está pago.")
            return False

        # Extrai produto_id e quantidade da referência (formato "produto_id:quantidade")
        produto_id = None
        quantidade = 1
        if pagamento.referencia and ":" in pagamento.referencia:
            try:
                produto_id, quantidade_str = pagamento.referencia.split(":")
                produto_id = int(produto_id)
                quantidade = int(quantidade_str)
            except (ValueError, TypeError):
                logger.error(f"Referência inválida no pagamento {pagamento_id}: {pagamento.referencia}")
                return False
        else:
            logger.error(f"Pagamento {pagamento_id} sem referência de produto.")
            return False

        # Busca produto e usuário
        produto = await session.get(Produto, produto_id)
        user = await session.get(User, pagamento.user_id)
        if not produto or not user:
            logger.error(f"Produto {produto_id} ou usuário {pagamento.user_id} não encontrado.")
            return False

        # Verifica estoque
        if produto.estoque < quantidade:
            logger.error(f"Estoque insuficiente para produto {produto_id}.")
            # Reembolso? Por enquanto apenas loga e retorna False
            return False

        # Seleciona itens do estoque
        result = await session.execute(
            select(EstoqueItem)
            .where(EstoqueItem.produto_id == produto_id, EstoqueItem.vendido == False)
            .limit(quantidade)
        )
        itens = result.scalars().all()
        if len(itens) < quantidade:
            logger.error(f"Não há itens suficientes no estoque para produto {produto_id}.")
            return False

        # Marca itens como vendidos
        for item in itens:
            item.vendido = True

        conteudos = [item.conteudo for item in itens]

        # Cria venda
        venda = Venda(
            id=uuid.uuid4(),
            user_id=user.id,
            produto_id=produto.id,
            quantidade=quantidade,
            valor_total=pagamento.valor,  # valor pago
            data_compra=datetime.now(),
            vencimento=calcular_vencimento(produto.garantia_dias),
            forma_pagamento="pix",
            status="pago",
            itens_entregues=conteudos,
        )
        session.add(venda)

        # Atualiza produto
        produto.estoque -= quantidade
        produto.vendidos += quantidade

        # Atualiza usuário (total gasto)
        user.total_gasto += pagamento.valor

        # Log
        log = Log(
            user_id=user.id,
            acao="compra_entregue_pix",
            detalhes={
                "venda_id": str(venda.id),
                "pagamento_id": str(pagamento.id),
                "produto_id": produto_id,
                "quantidade": quantidade,
            }
        )
        session.add(log)

        await session.commit()

        logger.info(f"Compra entregue via PIX: venda {venda.id}")
        return True


async def enviar_entrega_compra(venda_id: str, bot=None) -> bool:
    """
    Envia a mensagem de entrega da compra ao usuário via Telegram (se bot disponível).
    """
    from services.delivery import formatar_entrega, enviar_entrega_telegram

    async with async_session() as session:
        venda = await session.get(Venda, uuid.UUID(venda_id))
        if not venda:
            return False

        produto = await session.get(Produto, venda.produto_id)
        if not produto:
            return False

        # Busca itens entregues a partir do JSON
        conteudos = venda.itens_entregues or []
        if not conteudos:
            return False

        # Monta mensagem
        texto = await formatar_entrega(venda, produto, [EstoqueItem(conteudo=c) for c in conteudos])

        if bot:
            user = await session.get(User, venda.user_id)
            if user:
                enviado = await enviar_entrega_telegram(bot, user.id, texto)
                return enviado
        return False
