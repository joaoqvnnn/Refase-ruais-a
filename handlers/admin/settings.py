# ==============================================
# LARIZINHA STORE - HANDLER ADMIN CONFIGURAÇÕES
# ==============================================

import logging
from decimal import Decimal, InvalidOperation
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select
from database.connection import async_session
from database.models import Configuracao, Log
from keyboards.admin import admin_settings_menu_keyboard, admin_back_keyboard
from utils.decorators import admin_only
from utils.validators import validar_porcentagem, validar_valor_positivo

logger = logging.getLogger(__name__)
router = Router()

# ---------------------------------------------------------------
# MAPEAMENTO DAS CONFIGURAÇÕES EDITÁVEIS
# Cada chave tem descrição e tipo para validação
# ---------------------------------------------------------------
CONFIG_KEYS = {
    "min_recharge": {
        "descricao": "Valor mínimo de recarga (R$)",
        "tipo": "decimal",
        "default": "4.00",
    },
    "bonus_percent": {
        "descricao": "Bônus de recarga (%)",
        "tipo": "percent",
        "default": "10",
    },
    "min_bonus_value": {
        "descricao": "Valor mínimo para ganhar bônus (R$)",
        "tipo": "decimal",
        "default": "10.00",
    },
    "min_withdrawal": {
        "descricao": "Saque mínimo de afiliados (R$)",
        "tipo": "decimal",
        "default": "20.00",
    },
    "default_commission": {
        "descricao": "Comissão padrão de afiliados (%)",
        "tipo": "percent",
        "default": "10",
    },
    "pix_expiration": {
        "descricao": "Tempo de expiração do PIX (minutos)",
        "tipo": "int",
        "default": "10",
    },
    "support_whatsapp": {
        "descricao": "Número de WhatsApp do suporte",
        "tipo": "text",
        "default": "",
    },
    "support_email": {
        "descricao": "E-mail de suporte",
        "tipo": "text",
        "default": "",
    },
    "bot_name": {
        "descricao": "Nome do bot (exibido nas mensagens)",
        "tipo": "text",
        "default": "Larizinha Store",
    },
}


class SettingsForm(StatesGroup):
    waiting_key = State()
    waiting_value = State()


# ==============================================
# MENU PRINCIPAL DE CONFIGURAÇÕES
# ==============================================
@router.callback_query(F.data == "admin_settings")
@admin_only
async def admin_settings_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Configurações\n\n"
        "Selecione uma categoria:",
        reply_markup=admin_settings_menu_keyboard()
    )
    await callback.answer()


# ==============================================
# VISUALIZAR CONFIGURAÇÕES ATUAIS
# ==============================================
@router.callback_query(F.data == "admin_setting_view")
@admin_only
async def admin_setting_view(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Configuracao))
        configs = result.scalars().all()

    if not configs:
        # Usa valores padrão do mapeamento
        linhas = [f"{desc}: {val['default']}" for key, val in CONFIG_KEYS.items() for desc in [val['descricao']]]
    else:
        config_dict = {c.chave: c.valor for c in configs}
        linhas = []
        for chave, val in CONFIG_KEYS.items():
            valor_atual = config_dict.get(chave, val["default"])
            linhas.append(f"<b>{val['descricao']}</b>: {valor_atual}")

    texto = "⚙️ Configurações Atuais\n\n" + "\n".join(linhas)

    # Botão para editar cada configuração
    botoes = []
    for chave in CONFIG_KEYS:
        botoes.append([
            InlineKeyboardButton(
                text=f"✏️ {CONFIG_KEYS[chave]['descricao']}",
                callback_data=f"admin_setting_edit:{chave}"
            )
        ])
    botoes.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_settings")])
    teclado = InlineKeyboardMarkup(inline_keyboard=botoes)

    await callback.message.edit_text(texto, reply_markup=teclado)
    await callback.answer()


# ==============================================
# INICIAR EDIÇÃO DE UMA CONFIGURAÇÃO
# ==============================================
@router.callback_query(F.data.startswith("admin_setting_edit:"))
@admin_only
async def admin_setting_edit(callback: CallbackQuery, state: FSMContext):
    chave = callback.data.split(":")[1]
    if chave not in CONFIG_KEYS:
        await callback.answer("Configuração não encontrada.", show_alert=True)
        return

    await state.update_data(chave=chave)
    await state.set_state(SettingsForm.waiting_value)

    descricao = CONFIG_KEYS[chave]["descricao"]
    tipo = CONFIG_KEYS[chave]["tipo"]
    valor_atual = CONFIG_KEYS[chave]["default"]

    # Buscar valor no banco se existir
    async with async_session() as session:
        result = await session.execute(
            select(Configuracao).where(Configuracao.chave == chave)
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            valor_atual = cfg.valor

    texto = (
        f"✏️ Editar: <b>{descricao}</b>\n"
        f"Valor atual: {valor_atual}\n"
        f"Tipo esperado: {tipo}\n\n"
        "Digite o novo valor (ou /cancelar para abortar):"
    )
    await callback.message.answer(texto)
    await callback.answer()


# ==============================================
# RECEBER NOVO VALOR E SALVAR
# ==============================================
@router.message(SettingsForm.waiting_value)
@admin_only
async def settings_value_received(message: Message, state: FSMContext):
    if message.text.strip() == "/cancelar":
        await state.clear()
        await message.answer("Edição cancelada.")
        return

    dados = await state.get_data()
    chave = dados.get("chave")
    config_info = CONFIG_KEYS.get(chave)
    if not config_info:
        await state.clear()
        await message.answer("Erro: configuração inválida.")
        return

    novo_valor = message.text.strip()
    tipo = config_info["tipo"]

    # Valida conforme o tipo
    if tipo == "decimal":
        try:
            valor_decimal = Decimal(novo_valor.replace(",", "."))
            if valor_decimal < 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            await message.answer("Valor decimal inválido. Digite novamente ou /cancelar.")
            return
    elif tipo == "percent":
        try:
            percentual = Decimal(novo_valor.replace(",", "."))
            if not (Decimal("0") <= percentual <= Decimal("100")):
                raise ValueError
        except (ValueError, InvalidOperation):
            await message.answer("Percentual inválido (0 a 100). Digite novamente ou /cancelar.")
            return
    elif tipo == "int":
        try:
            int_valor = int(novo_valor)
            if int_valor < 0:
                raise ValueError
        except ValueError:
            await message.answer("Número inteiro inválido. Digite novamente ou /cancelar.")
            return
    elif tipo == "text":
        if not novo_valor:
            await message.answer("Texto vazio. Digite novamente ou /cancelar.")
            return

    # Salva no banco
    async with async_session() as session:
        result = await session.execute(
            select(Configuracao).where(Configuracao.chave == chave)
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.valor = novo_valor
        else:
            nova_config = Configuracao(chave=chave, valor=novo_valor, descricao=config_info["descricao"])
            session.add(nova_config)

        # Log
        log = Log(
            user_id=message.from_user.id,
            acao="configuracao_alterada",
            detalhes={"chave": chave, "novo_valor": novo_valor}
        )
        session.add(log)
        await session.commit()

    await message.answer(f"✅ Configuração <b>{config_info['descricao']}</b> atualizada para: {novo_valor}")
    await state.clear()
