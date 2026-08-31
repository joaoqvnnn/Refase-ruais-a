# ==============================================
# LARIZINHA STORE - HANDLER ADMIN MENSAGENS PERSONALIZADAS
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select
from database.connection import async_session
from database.models import MensagemPersonalizada, Log
from keyboards.admin import admin_messages_menu_keyboard, admin_back_keyboard
from texts.client import DEFAULT_TEXTS
from utils.decorators import admin_only

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA EDITAR MENSAGEM
# ==============================================
class MessageEditForm(StatesGroup):
    waiting_novo_texto = State()
    waiting_confirmacao = State()


# ==============================================
# MENU PRINCIPAL DE MENSAGENS
# ==============================================
@router.callback_query(F.data == "admin_messages")
@admin_only
async def admin_messages_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💬 Editar Mensagens\n\n"
        "Aqui você pode personalizar todas as mensagens exibidas aos clientes.\n"
        "Selecione uma opção:",
        reply_markup=admin_messages_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR MENSAGENS DISPONÍVEIS
# ==============================================
@router.callback_query(F.data == "admin_message_list")
@admin_only
async def admin_message_list(callback: CallbackQuery, page: int = 0):
    """
    Lista todas as chaves de mensagens personalizáveis com paginação.
    """
    chaves = list(DEFAULT_TEXTS.keys())
    itens_por_pagina = 10
    total_paginas = (len(chaves) + itens_por_pagina - 1) // itens_por_pagina
    inicio = page * itens_por_pagina
    fim = inicio + itens_por_pagina
    pagina_chaves = chaves[inicio:fim]

    botoes = []
    for chave in pagina_chaves:
        botoes.append([
            InlineKeyboardButton(
                text=f"✏️ {chave}",
                callback_data=f"admin_message_edit:{chave}"
            )
        ])

    # Navegação entre páginas
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_message_page:{page-1}"))
    if page < total_paginas - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_message_page:{page+1}"))
    if nav:
        botoes.append(nav)

    botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_messages")])
    teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    texto = (
        "📝 Mensagens Personalizáveis\n\n"
        f"Página {page+1}/{total_paginas}\n"
        "Selecione uma mensagem para editar:"
    )

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_message_page:"))
@admin_only
async def admin_message_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await admin_message_list(callback, page)


# ==============================================
# EDITAR MENSAGEM SELECIONADA
# ==============================================
@router.callback_query(F.data.startswith("admin_message_edit:"))
@admin_only
async def admin_message_edit(callback: CallbackQuery, state: FSMContext):
    chave = callback.data.split(":")[1]
    if chave not in DEFAULT_TEXTS:
        await callback.answer("Mensagem não encontrada.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(MensagemPersonalizada).where(MensagemPersonalizada.chave == chave)
        )
        msg_db = result.scalar_one_or_none()

    texto_atual = msg_db.texto if msg_db else DEFAULT_TEXTS[chave]

    await state.update_data(chave=chave)
    await state.set_state(MessageEditForm.waiting_novo_texto)

    await callback.message.answer(
        f"✏️ Editando mensagem: <b>{chave}</b>\n\n"
        "Texto atual:\n"
        f"<pre>{texto_atual}</pre>\n\n"
        "Envie o novo texto. Use {variável} para dados dinâmicos.\n"
        "Envie /cancelar para abortar."
    )
    await callback.answer()


@router.message(MessageEditForm.waiting_novo_texto)
@admin_only
async def message_novo_texto(message: Message, state: FSMContext):
    if message.text == "/cancelar":
        await state.clear()
        await message.answer("Edição cancelada.")
        return

    novo_texto = message.text
    if not novo_texto.strip():
        await message.answer("Texto vazio. Envie um texto válido ou /cancelar.")
        return

    dados = await state.get_data()
    chave = dados["chave"]

    await state.update_data(novo_texto=novo_texto)
    await state.set_state(MessageEditForm.waiting_confirmacao)

    await message.answer(
        f"Confirmar alteração da mensagem <b>{chave}</b>?\n\n"
        "Pré-visualização:\n"
        f"<pre>{novo_texto}</pre>\n\n"
        "Envie /confirmar para salvar ou /cancelar para abortar."
    )


@router.message(MessageEditForm.waiting_confirmacao)
@admin_only
async def message_confirmacao(message: Message, state: FSMContext):
    if message.text == "/cancelar":
        await state.clear()
        await message.answer("Edição cancelada.")
        return

    if message.text != "/confirmar":
        await message.answer("Envie /confirmar para salvar ou /cancelar para abortar.")
        return

    dados = await state.get_data()
    chave = dados["chave"]
    novo_texto = dados["novo_texto"]

    async with async_session() as session:
        result = await session.execute(
            select(MensagemPersonalizada).where(MensagemPersonalizada.chave == chave)
        )
        msg_db = result.scalar_one_or_none()

        if msg_db:
            msg_db.texto = novo_texto
        else:
            nova_msg = MensagemPersonalizada(chave=chave, texto=novo_texto)
            session.add(nova_msg)

        # Log
        log = Log(
            user_id=message.from_user.id,
            acao="mensagem_editada",
            detalhes={"chave": chave}
        )
        session.add(log)
        await session.commit()

    await message.answer(f"✅ Mensagem <b>{chave}</b> atualizada com sucesso!")
    await state.clear()
