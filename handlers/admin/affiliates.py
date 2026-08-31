# ==============================================
# LARIZINHA STORE - HANDLER ADMIN AFILIADOS E SAQUES
# ==============================================

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func
from database.connection import async_session
from database.models import Afiliado, SaqueAfiliado, User, Log
from keyboards.admin import admin_affiliates_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only
from utils.validators import validar_porcentagem

logger = logging.getLogger(__name__)
router = Router()


# ==============================================
# FSM PARA CONFIGURAR COMISSÃO E PROCESSAR SAQUES
# ==============================================
class AffiliateSettingsForm(StatesGroup):
    waiting_user_id = State()
    waiting_commission = State()


class WithdrawalProcessForm(StatesGroup):
    waiting_withdrawal_id = State()


# ==============================================
# MENU PRINCIPAL DE AFILIADOS
# ==============================================
@router.callback_query(F.data == "admin_affiliates")
@admin_only
async def admin_affiliates_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 Afiliados e Saques\n\nEscolha uma ação:",
        reply_markup=admin_affiliates_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# LISTAR AFILIADOS
# ==============================================
@router.callback_query(F.data == "admin_affiliate_list")
@admin_only
async def admin_affiliate_list(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Afiliado, User)
            .join(User, User.id == Afiliado.user_id)
            .order_by(Afiliado.total_ganho.desc())
            .limit(20)
        )
        dados = result.all()

    if not dados:
        texto = "Nenhum afiliado registrado."
        teclado = admin_affiliates_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for af, user in dados:
            nome = user.first_name or user.username or str(af.user_id)
            linhas.append(
                f"#{af.user_id} {nome} | Comissão: {float(af.comissao_percent):.1f}% | "
                f"Indicações: {af.total_indicacoes} | Saldo: R$ {float(af.saldo_comissoes):.2f}"
            )
            botoes.append([
                InlineKeyboardButton(
                    text=f"✏️ Comissão {nome}",
                    callback_data=f"admin_affiliate_commission:{af.user_id}"
                )
            ])
        texto = "👥 Afiliados (top 20):\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_affiliates")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# CONFIGURAR COMISSÃO INDIVIDUAL
# ==============================================
@router.callback_query(F.data.startswith("admin_affiliate_commission:"))
@admin_only
async def admin_affiliate_commission(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])

    await state.update_data(user_id=user_id)
    await state.set_state(AffiliateSettingsForm.waiting_commission)
    await callback.message.answer(
        f"Digite o novo percentual de comissão para o usuário #{user_id} (0 a 100):"
    )
    await callback.answer()


@router.message(AffiliateSettingsForm.waiting_commission)
@admin_only
async def affiliate_commission_received(message: Message, state: FSMContext):
    try:
        percentual = Decimal(message.text.replace(",", "."))
        if percentual < 0 or percentual > 100:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("Percentual inválido. Use um valor entre 0 e 100.")
        return

    dados = await state.get_data()
    user_id = dados["user_id"]

    async with async_session() as session:
        afiliado = await session.get(Afiliado, user_id)
        if not afiliado:
            # Cria registro se não existir
            afiliado = Afiliado(user_id=user_id, comissao_percent=percentual)
            session.add(afiliado)
        else:
            afiliado.comissao_percent = percentual

        # Log
        log = Log(
            user_id=message.from_user.id,
            acao="comissao_afiliado_alterada",
            detalhes={"afiliado_id": user_id, "nova_comissao": float(percentual)}
        )
        session.add(log)
        await session.commit()

    await message.answer(
        f"✅ Comissão do afiliado #{user_id} atualizada para {float(percentual):.1f}%!"
    )
    await state.clear()


# ==============================================
# SAQUES PENDENTES
# ==============================================
@router.callback_query(F.data == "admin_withdrawal_pending")
@admin_only
async def admin_withdrawal_pending(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(SaqueAfiliado)
            .where(SaqueAfiliado.status == "pendente")
            .order_by(SaqueAfiliado.data_solicitacao)
        )
        saques = result.scalars().all()

    if not saques:
        texto = "Não há saques pendentes."
        teclado = admin_affiliates_menu_keyboard()
    else:
        linhas = []
        botoes = []
        for s in saques:
            linhas.append(
                f"#{s.id} | User {s.user_id} | R$ {float(s.valor):.2f} | "
                f"Chave PIX: {s.chave_pix[:20]}... | {s.data_solicitacao.strftime('%d/%m/%Y')}"
            )
            botoes.append([
                InlineKeyboardButton(
                    text=f"✅ Aprovar #{s.id}",
                    callback_data=f"admin_withdrawal_approve:{s.id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ Recusar #{s.id}",
                    callback_data=f"admin_withdrawal_reject:{s.id}"
                ),
            ])
        texto = "💰 Saques Pendentes:\n\n" + "\n".join(linhas)
        botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_affiliates")])
        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# APROVAR SAQUE
# ==============================================
@router.callback_query(F.data.startswith("admin_withdrawal_approve:"))
@admin_only
async def admin_withdrawal_approve(callback: CallbackQuery):
    saque_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        saque = await session.get(SaqueAfiliado, saque_id)
        if not saque:
            await callback.answer("Saque não encontrado.", show_alert=True)
            return

        if saque.status != "pendente":
            await callback.answer("Saque já processado.", show_alert=True)
            return

        saque.status = "aprovado"
        saque.data_processamento = datetime.now()

        # Log
        log = Log(
            user_id=callback.from_user.id,
            acao="saque_aprovado",
            detalhes={"saque_id": saque_id, "afiliado_id": saque.user_id, "valor": float(saque.valor)}
        )
        session.add(log)
        await session.commit()

    await callback.answer("Saque aprovado!", show_alert=True)
    await admin_withdrawal_pending(callback)


# ==============================================
# RECUSAR SAQUE
# ==============================================
@router.callback_query(F.data.startswith("admin_withdrawal_reject:"))
@admin_only
async def admin_withdrawal_reject(callback: CallbackQuery):
    saque_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        saque = await session.get(SaqueAfiliado, saque_id)
        if not saque:
            await callback.answer("Saque não encontrado.", show_alert=True)
            return

        if saque.status != "pendente":
            await callback.answer("Saque já processado.", show_alert=True)
            return

        # Devolve o valor ao saldo de comissões do afiliado
        afiliado = await session.get(Afiliado, saque.user_id)
        if afiliado:
            afiliado.saldo_comissoes += saque.valor

        saque.status = "recusado"
        saque.data_processamento = datetime.now()

        # Log
        log = Log(
            user_id=callback.from_user.id,
            acao="saque_recusado",
            detalhes={"saque_id": saque_id, "afiliado_id": saque.user_id, "valor": float(saque.valor)}
        )
        session.add(log)
        await session.commit()

    await callback.answer("Saque recusado. Valor devolvido ao saldo.", show_alert=True)
    await admin_withdrawal_pending(callback)


# ==============================================
# CONFIGURAÇÃO GLOBAL DE COMISSÃO (menu)
# ==============================================
@router.callback_query(F.data == "admin_affiliate_settings")
@admin_only
async def admin_affiliate_settings(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AffiliateSettingsForm.waiting_commission)
    await callback.message.answer(
        "Digite o percentual de comissão padrão (0 a 100) para novos afiliados:"
    )
    await callback.answer()
