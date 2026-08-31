# ==============================================
# LARIZINHA STORE - HANDLER SISTEMA DE ALERTAS
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from sqlalchemy import select, func
from database.connection import async_session
from database.models import Alerta, Produto
from keyboards.client import alerts_keyboard, back_to_main_keyboard
from texts.client import get_message

logger = logging.getLogger(__name__)
router = Router()


async def _obter_produtos_paginados(pagina: int = 0, itens_por_pagina: int = 10) -> tuple[list, int]:
    """
    Retorna uma lista de produtos ativos e o total de páginas.
    """
    async with async_session() as session:
        # Conta total de produtos ativos
        result_count = await session.execute(
            select(func.count(Produto.id)).where(Produto.ativo == True)
        )
        total_produtos = result_count.scalar() or 0

        # Busca produtos da página
        result = await session.execute(
            select(Produto.id, Produto.nome, Produto.emoji)
            .where(Produto.ativo == True)
            .order_by(Produto.nome)
            .offset(pagina * itens_por_pagina)
            .limit(itens_por_pagina)
        )
        produtos = result.all()

        total_paginas = (total_produtos + itens_por_pagina - 1) // itens_por_pagina
        return produtos, total_paginas


async def _obter_alertas_usuario(user_id: int) -> set[int]:
    """
    Retorna um conjunto com os IDs dos produtos que o usuário está monitorando.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Alerta.produto_id).where(Alerta.user_id == user_id, Alerta.ativo == True)
        )
        return set(result.scalars().all())


async def _montar_lista_produtos_alertas(user_id: int, pagina: int = 0) -> tuple[str, object, int]:
    """
    Monta o texto e o teclado de alertas para uma página.
    Retorna (texto, teclado, total_paginas).
    """
    produtos, total_paginas = await _obter_produtos_paginados(pagina)
    alertas_ativos = await _obter_alertas_usuario(user_id)

    if not produtos:
        return (
            "📱 Nenhum produto disponível para alerta.",
            back_to_main_keyboard(),
            0
        )

    lista_produtos = []
    for prod_id, nome, emoji in produtos:
        status = "✅" if prod_id in alertas_ativos else "❌"
        lista_produtos.append({
            "id": prod_id,
            "nome": f"{emoji} {nome}" if emoji else nome,
            "alerta_ativo": prod_id in alertas_ativos,
        })

    texto = get_message("alerta")
    teclado = alerts_keyboard(lista_produtos, pagina, total_paginas)
    return texto, teclado, total_paginas


@router.callback_query(F.data == "menu_alerts")
async def menu_alerts(callback: CallbackQuery):
    await show_alerts(callback, 0)


@router.callback_query(F.data.startswith("alerta_pag:"))
async def alerta_pagina(callback: CallbackQuery):
    try:
        pagina = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        pagina = 0

    await show_alerts(callback, pagina)


@router.callback_query(F.data.startswith("alerta:"))
async def alternar_alerta(callback: CallbackQuery):
    """
    Ativa/desativa o alerta para um produto, atualizando a mensagem.
    """
    try:
        produto_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Produto inválido.", show_alert=True)
        return

    user_id = callback.from_user.id

    async with async_session() as session:
        # Verifica se o alerta já existe
        result = await session.execute(
            select(Alerta).where(
                Alerta.user_id == user_id,
                Alerta.produto_id == produto_id,
            )
        )
        alerta = result.scalar_one_or_none()

        if alerta:
            # Alterna o estado
            alerta.ativo = not alerta.ativo
            await session.commit()
        else:
            # Cria novo alerta
            novo_alerta = Alerta(
                user_id=user_id,
                produto_id=produto_id,
                ativo=True,
            )
            session.add(novo_alerta)
            await session.commit()

    # Obtém a página atual para re-renderizar
    # Assumimos que o callback contém a página? Não; vamos usar a página 0 por simplicidade
    # Em produção, é recomendável armazenar a página no callback_data
    await show_alerts(callback, 0)
    await callback.answer()


async def show_alerts(callback: CallbackQuery, pagina: int = 0):
    """
    Exibe a tela de alertas com a lista de produtos.
    """
    user_id = callback.from_user.id
    texto, teclado, _ = await _montar_lista_produtos_alertas(user_id, pagina)

    if hasattr(callback, "message"):
        await callback.message.edit_text(texto, reply_markup=teclado)
        await callback.answer()
    else:
        # Caso seja chamado por outro handler, mas normalmente usamos callback
        await callback.answer(texto, reply_markup=teclado)


@router.callback_query(F.data == "back_to_main")
async def voltar_menu(callback: CallbackQuery):
    # Essa função é reutilizada de start.py; aqui apenas redireciona
    from handlers.client.start import voltar_menu_principal
    await voltar_menu_principal(callback)
