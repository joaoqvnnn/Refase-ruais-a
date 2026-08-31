# ==============================================
# LARIZINHA STORE - TECLADOS INLINE DO ADMIN
# ==============================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado principal do painel administrativo.
    """
    buttons = [
        [InlineKeyboardButton(text="📦 Gerenciar Produtos", callback_data="admin_products")],
        [InlineKeyboardButton(text="📁 Gerenciar Categorias", callback_data="admin_categories")],
        [InlineKeyboardButton(text="💬 Editar Mensagens", callback_data="admin_messages")],
        [InlineKeyboardButton(text="👥 Usuários", callback_data="admin_users")],
        [InlineKeyboardButton(text="🎁 Gift Cards", callback_data="admin_giftcards")],
        [InlineKeyboardButton(text="💰 Afiliados e Saques", callback_data="admin_affiliates")],
        [InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_statistics")],
        [InlineKeyboardButton(text="💳 Pagamentos", callback_data="admin_payments")],
        [InlineKeyboardButton(text="⚙️ Configurações", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📨 Enviar Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📋 Logs", callback_data="admin_logs")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_back_keyboard(callback_data: str = "admin_panel") -> InlineKeyboardMarkup:
    """
    Teclado com botão para voltar ao painel ou seção anterior.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data=callback_data)]
    ])


def admin_products_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de gerenciamento de produtos.
    """
    buttons = [
        [InlineKeyboardButton(text="➕ Adicionar Produto", callback_data="admin_product_add")],
        [InlineKeyboardButton(text="📋 Listar Produtos", callback_data="admin_product_list")],
        [InlineKeyboardButton(text="📦 Adicionar Estoque", callback_data="admin_stock_add")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_categories_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de gerenciamento de categorias.
    """
    buttons = [
        [InlineKeyboardButton(text="➕ Adicionar Categoria", callback_data="admin_category_add")],
        [InlineKeyboardButton(text="📋 Listar Categorias", callback_data="admin_category_list")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_messages_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de edição de mensagens.
    """
    buttons = [
        [InlineKeyboardButton(text="📝 Listar Mensagens", callback_data="admin_message_list")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_users_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de gerenciamento de usuários.
    """
    buttons = [
        [InlineKeyboardButton(text="🔍 Buscar Usuário", callback_data="admin_user_search")],
        [InlineKeyboardButton(text="👥 Listar Usuários", callback_data="admin_user_list")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_giftcards_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de gift cards.
    """
    buttons = [
        [InlineKeyboardButton(text="🎁 Gerar Gift Cards", callback_data="admin_giftcard_generate")],
        [InlineKeyboardButton(text="📋 Listar Gift Cards", callback_data="admin_giftcard_list")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_affiliates_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de afiliados e saques.
    """
    buttons = [
        [InlineKeyboardButton(text="👥 Ver Afiliados", callback_data="admin_affiliate_list")],
        [InlineKeyboardButton(text="💰 Saques Pendentes", callback_data="admin_withdrawal_pending")],
        [InlineKeyboardButton(text="⚙️ Configurar Comissão", callback_data="admin_affiliate_settings")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_payments_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de pagamentos.
    """
    buttons = [
        [InlineKeyboardButton(text="💳 Pagamentos Pendentes", callback_data="admin_payment_pending")],
        [InlineKeyboardButton(text="✅ Pagamentos Aprovados", callback_data="admin_payment_approved")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_settings_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de configurações.
    """
    buttons = [
        [InlineKeyboardButton(text="💳 Gateway de Pagamento", callback_data="admin_setting_gateway")],
        [InlineKeyboardButton(text="💰 Recarga e Bônus", callback_data="admin_setting_recharge")],
        [InlineKeyboardButton(text="🤝 Afiliados", callback_data="admin_setting_affiliate")],
        [InlineKeyboardButton(text="🔒 Segurança", callback_data="admin_setting_security")],
        [InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_setting_broadcast")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de broadcast.
    """
    buttons = [
        [InlineKeyboardButton(text="📨 Enviar para Todos", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton(text="👤 Enviar para Usuário", callback_data="admin_broadcast_user")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_logs_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de logs.
    """
    buttons = [
        [InlineKeyboardButton(text="📋 Ver Logs Recentes", callback_data="admin_log_view")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
