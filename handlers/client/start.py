# ==============================================
# LARIZINHA STORE - HANDLER /start E MENU PRINCIPAL
# ==============================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database.connection import async_session
from database.models import User, Afiliado
from keyboards.client import main_menu_keyboard
from texts.client import get_message
from config import BOT_USERNAME

logger = logging.getLogger(__name__)
router = Router()


async def get_or_create_user(user_id: int, username: str | None, first_name: str, last_name: str | None = None) -> User:
    """
    Busca o usuário no banco ou cria um novo.
    Retorna o objeto User.
    """
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name or "Cliente",
                last_name=last_name,
                saldo=0.0,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Novo usuário cadastrado: {user_id} ({first_name})")
        return user


async def registrar_indicacao(user_id: int, indicador_id: int) -> None:
    """
    Registra a indicação de afiliado, caso seja válida.
    """
    if user_id == indicador_id:
        return  # não pode indicar a si mesmo

    async with async_session() as session:
        user = await session.get(User, user_id)
        if user and not user.indicado_por:
            # Verifica se o indicador existe
            indicador = await session.get(User, indicador_id)
            if indicador:
                user.indicado_por = indicador_id
                await session.commit()

                # Incrementa contador de indicações do afiliado
                afiliado = await session.get(Afiliado, indicador_id)
                if afiliado:
                    afiliado.total_indicacoes += 1
                else:
                    afiliado = Afiliado(
                        user_id=indicador_id,
                        total_indicacoes=1,
                    )
                    session.add(afiliado)
                await session.commit()
                logger.info(f"Usuário {user_id} indicado por {indicador_id}")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handler do comando /start.
    Registra o usuário (e indicação, se houver) e exibe o menu principal.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Cria ou obtém o usuário
    user = await get_or_create_user(user_id, username, first_name, last_name)

    # Verifica se veio de link de afiliado: /start {indicador_id}
    args = message.text.split()
    if len(args) > 1:
        try:
            indicador_id = int(args[1])
            await registrar_indicacao(user_id, indicador_id)
        except ValueError:
            pass  # parâmetro inválido, ignora

    # Monta a mensagem de boas-vindas
    saldo = float(user.saldo)
    texto = await get_message(
        "start",
        user_id=user_id,
        username=username or "Não definido",
        first_name=first_name,
        saldo=f"{saldo:.2f}",
        NOME_BOT=BOT_USERNAME,
    )

    # Envia a mensagem com o menu principal
    await message.answer(texto, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "back_to_main")
async def voltar_menu_principal(callback: CallbackQuery) -> None:
    """
    Retorna ao menu principal quando o usuário clica em "Voltar".
    """
    user_id = callback.from_user.id

    async with async_session() as session:
        user = await session.get(User, user_id)

    saldo = float(user.saldo) if user else 0.0
    texto = await get_message(
        "start",
        user_id=user_id,
        username=callback.from_user.username or "Não definido",
        first_name=callback.from_user.first_name,
        saldo=f"{saldo:.2f}",
        NOME_BOT=BOT_USERNAME,
    )

    # Edita a mensagem atual para o menu principal
    await callback.message.edit_text(texto, reply_markup=main_menu_keyboard())
    await callback.answer()
