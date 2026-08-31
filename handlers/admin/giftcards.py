# ==============================================
# LARIZINHA STORE - HANDLER ADMIN GIFT CARDS
# ==============================================

import logging
import random
import string
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import GiftCard, Log
from keyboards.admin import admin_giftcards_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only
from utils.validators import validar_valor_positivo

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA GERAÇÃO DE GIFT CARDS
# ==============================================
class GiftCardForm(StatesGroup):
    waiting_valor = State()
    waiting_quantidade = State()
    waiting_expiracao = State()
    waiting_confirmacao = State()


def gerar_codigo_giftcard(tamanho: int = 12) -> str:
    """
    Gera um código alfanumérico maiúsculo para gift card.
    """
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choices(caracteres, k=tamanho))


# ==============================================
# MENU PRINCIPAL DE GIFT CARDS
# ==============================================
@router.callback_query(F.data == "admin_giftcards")
@admin_only
async def admin_giftcards_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎁 Gerenciar Gift Cards\n\n"
        "Escolha uma ação:",
        reply_markup=admin_giftcards_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# GERAR GIFT CARDS (FSM)
# ==============================================
@router.callback_query(F.data == "admin_giftcard_generate")
@admin_only
async def admin_giftcard_generate_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiftCardForm.waiting_valor)
    await callback.message.answer(
        "Digite o valor de cada gift card (ex: 20.00):"
    )
    await callback.answer()


@router.message(GiftCardForm.waiting_valor)
@admin_only
async def giftcard_valor_recebido(message: Message, state: FSMContext):
    try:
        valor = Decimal(message.text.replace(",", "."))
        if valor <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("Valor inválido.")
        return

    await state.update_data(valor=valor)
    await state.set_state(GiftCardForm.waiting_quantidade)
    await message.answer("Digite a quantidade de gift cards a gerar:")


@router.message(GiftCardForm.waiting_quantidade)
@admin_only
async def giftcard_quantidade_recebida(message: Message, state: FSMContext):
    try:
        quantidade = int(message.text.strip())
        if quantidade <= 0 or quantidade > 100:
            raise ValueError
    except ValueError:
        await message.answer("Quantidade inválida. Use um número entre 1 e 100.")
        return

    await state.update_data(quantidade=quantidade)
    await state.set_state(GiftCardForm.waiting_expiracao)
    await message.answer(
        "Digite a data de expiração no formato DD/MM/AAAA ou /pular para sem expiração:"
    )


@router.message(GiftCardForm.waiting_expiracao)
@admin_only
async def giftcard_expiracao_recebida(message: Message, state: FSMContext):
    expira_em = None
    if message.text.strip() != "/pular":
        try:
            expira_em = datetime.strptime(message.text.strip(), "%d/%m/%Y").date()
            if expira_em < date.today():
                await message.answer("Data de expiração não pode ser no passado.")
                return
        except ValueError:
            await message.answer("Data inválida. Use DD/MM/AAAA ou /pular.")
            return

    dados = await state.get_data()
    await state.update_data(expira_em=expira_em)
    await state.set_state(GiftCardForm.waiting_confirmacao)

    resumo = (
        "Confirme a geração de gift cards:\n\n"
        f"Valor: R$ {float(dados['valor']):.2f}\n"
        f"Quantidade: {dados['quantidade']}\n"
        f"Expira em: {expira_em.strftime('%d/%m/%Y') if expira_em else 'Sem expiração'}\n\n"
        "Envie /confirmar para gerar ou /cancelar para abortar."
    )
    await message.answer(resumo)


@router.message(GiftCardForm.waiting_confirmacao)
@admin_only
async def giftcard_confirmacao(message: Message, state: FSMContext):
    if message.text.strip() != "/confirmar":
        await message.answer("Envie /confirmar para gerar ou /cancelar para abortar.")
        return

    dados = await state.get_data()
    valor = dados["valor"]
    quantidade = dados["quantidade"]
    expira_em = dados.get("expira_em")

    codigos_gerados = []
    async with async_session() as session:
        for _ in range(quantidade):
            # Gera código único
            while True:
                codigo = gerar_codigo_giftcard()
                # Verifica se já existe
                result = await session.execute(
                    select(GiftCard).where(GiftCard.codigo == codigo)
                )
                if not result.scalar_one_or_none():
                    break

            giftcard = GiftCard(
                codigo=codigo,
                valor=valor,
                usado=False,
                expira_em=expira_em,
                data_criacao=datetime.now(),
            )
            session.add(giftcard)
            codigos_gerados.append(codigo)

        # Log
        log = Log(
            user_id=message.from_user.id,
            acao="giftcards_gerados",
            detalhes={
                "quantidade": quantidade,
                "valor": float(valor),
                "expira_em": str(expira_em) if expira_em else None,
            }
        )
        session.add(log)
        await session.commit()

    # Monta resposta com os códigos
    lista_codigos = "\n".join(codigos_gerados)
    await message.answer(
        f"✅ {quantidade} gift card(s) gerado(s) com sucesso!\n\n"
        f"Valor: R$ {float(valor):.2f}\n"
        f"Expira em: {expira_em.strftime('%d/%m/%Y') if expira_em else 'Sem expiração'}\n\n"
        f"Códigos:\n<code>{lista_codigos}</code>"
    )
    await state.clear()


# ==============================================
# LISTAR GIFT CARDS
# ==============================================
@router.callback_query(F.data == "admin_giftcard_list")
@admin_only
async def admin_giftcard_list(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(GiftCard).order_by(GiftCard.data_criacao.desc()).limit(10)
        )
        giftcards = result.scalars().all()

    if not giftcards:
        texto = "Nenhum gift card gerado."
        teclado = admin_giftcards_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for gc in giftcards:
            status = "usado" if gc.usado else "disponível"
            expira = gc.expira_em.strftime('%d/%m/%Y') if gc.expira_em else "sem expiração"
            linhas.append(
                f"<code>{gc.codigo}</code> | R$ {float(gc.valor):.2f} | {status} | expira: {expira}"
            )
            if not gc.usado:
                botoes.append([
                    InlineKeyboardButton(
                        text=f"❌ Revogar {gc.codigo}",
                        callback_data=f"admin_giftcard_revoke:{gc.id}"
                    )
                ])
        texto = "🎁 Gift Cards (últimos 10):\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_giftcards")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# REVOGAR GIFT CARD
# ==============================================
@router.callback_query(F.data.startswith("admin_giftcard_revoke:"))
@admin_only
async def admin_giftcard_revoke(callback: CallbackQuery):
    giftcard_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        giftcard = await session.get(GiftCard, giftcard_id)
        if not giftcard:
            await callback.answer("Gift card não encontrado.", show_alert=True)
            return

        if giftcard.usado:
            await callback.answer("Gift card já utilizado/revogado.", show_alert=True)
            return

        # Marca como usado (revogado)
        giftcard.usado = True
        giftcard.usado_por = None  # sem usuário
        giftcard.data_uso = datetime.now()

        # Log
        log = Log(
            user_id=callback.from_user.id,
            acao="giftcard_revogado",
            detalhes={"giftcard_id": giftcard_id, "codigo": giftcard.codigo}
        )
        session.add(log)
        await session.commit()

    await callback.answer("Gift card revogado com sucesso!", show_alert=True)
    await admin_giftcard_list(callback)
