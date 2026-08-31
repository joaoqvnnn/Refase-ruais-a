# ==============================================
# LARIZINHA STORE - TECLADOS INLINE DO CLIENTE
# ==============================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu principal exibido após /start.
    """
    buttons = [
        [InlineKeyboardButton(text="🛍 Comprar Produtos", callback_data="menu_catalog")],
        [InlineKeyboardButton(text="💰 Recarregar Saldo", callback_data="menu_recharge")],
        [InlineKeyboardButton(text="👤 Meu Perfil", callback_data="menu_profile")],
        [InlineKeyboardButton(text="💎 Ser Afiliado", callback_data="menu_affiliate")],
        [InlineKeyboardButton(text="🏆 Top Rankings", callback_data="menu_rankings")],
        [InlineKeyboardButton(text="📞 Atendimento", callback_data="menu_support")],
        [InlineKeyboardButton(text="ℹ️ Sobre o Bot", callback_data="menu_about")],
        [InlineKeyboardButton(text="🔍 Pesquisar Serviço", switch_inline_query_current_chat="")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado com botão único para voltar ao menu principal.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")]
    ])


def catalog_keyboard(categorias: list) -> InlineKeyboardMarkup:
    """
    Teclado com categorias e botão de voltar.
    `categorias` é uma lista de dicionários: {id, nome, emoji}
    """
    buttons = []
    for cat in categorias:
        buttons.append([
            InlineKeyboardButton(
                text=f"{cat.get('emoji', '📁')} {cat['nome']}",
                callback_data=f"categoria:{cat['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_keyboard(produtos: list, categoria_id: int = None) -> InlineKeyboardMarkup:
    """
    Teclado com produtos de uma categoria.
    `produtos` é uma lista de dicionários: {id, nome, emoji, preco}
    """
    buttons = []
    for prod in produtos:
        buttons.append([
            InlineKeyboardButton(
                text=f"{prod.get('emoji', '🛒')} {prod['nome']} - R$ {float(prod['preco']):.2f}",
                callback_data=f"produto:{prod['id']}"
            )
        ])
    # Botão de voltar para categorias
    if categoria_id is not None:
        buttons.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="categoria_voltar")])
    else:
        buttons.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="menu_catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_details_keyboard(produto_id: int, saldo_suficiente: bool) -> InlineKeyboardMarkup:
    """
    Teclado de detalhes do produto com ações de compra.
    """
    buttons = [
        [
            InlineKeyboardButton(text="💳 Comprar", callback_data=f"comprar:{produto_id}"),
            InlineKeyboardButton(text="🔢 Comprar Mais de Um", callback_data=f"comprar_multi:{produto_id}")
        ],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def insufficient_balance_keyboard(valor: float, produto_id: int = None, tipo: str = "produto") -> InlineKeyboardMarkup:
    """
    Teclado para saldo insuficiente: gerar PIX ou cancelar.
    """
    buttons = [
        [InlineKeyboardButton(text=f"💠 Gerar PIX de R$ {valor:.2f}", callback_data=f"gerar_pix:{tipo}:{produto_id or 0}:{valor}")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_compra")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_waiting_keyboard(payment_id: str, codigo_pix: str) -> InlineKeyboardMarkup:
    """
    Teclado exibido após gerar PIX: aguardar pagamento, copiar PIX, cancelar.
    """
    buttons = [
        [InlineKeyboardButton(text="🔄 Aguardando Pagamento", callback_data=f"verificar_pagamento:{payment_id}")],
        [InlineKeyboardButton(text="📋 Copiar PIX", callback_data=f"copiar_pix:{payment_id}")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_pagamento")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de perfil.
    """
    buttons = [
        [InlineKeyboardButton(text="🛍 Histórico de Compras", callback_data="historico")],
        [InlineKeyboardButton(text="🎁 Resgatar Gift Card", callback_data="giftcard")],
        [InlineKeyboardButton(text="✏️ Alterar Dados", callback_data="alterar_dados")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def history_navigation_keyboard(indice: int, total: int, venda_id: str = None) -> InlineKeyboardMarkup:
    """
    Teclado de navegação do histórico (anterior, próxima, ações, voltar).
    """
    buttons = []
    nav = []
    if indice > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Anterior", callback_data=f"hist_ant:{indice}"))
    if indice < total:
        nav.append(InlineKeyboardButton(text="➡️ Próxima", callback_data=f"hist_prox:{indice}"))
    if nav:
        buttons.append(nav)

    if venda_id:
        buttons.append([
            InlineKeyboardButton(text="📧 Receber por Email", callback_data=f"enviar_email:{venda_id}"),
            InlineKeyboardButton(text="📱 Receber por WhatsApp", callback_data=f"enviar_whatsapp:{venda_id}"),
        ])
        buttons.append([
            InlineKeyboardButton(text="💬 Mostrar no Telegram", callback_data=f"mostrar_conteudo:{venda_id}")
        ])

    buttons.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="menu_profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def giftcard_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado da tela de resgate de gift card.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_giftcard")]
    ])


def alterar_dados_keyboard(whatsapp: str) -> InlineKeyboardMarkup:
    """
    Teclado de alteração de dados.
    """
    whatsapp_text = f"📱 WhatsApp: {whatsapp}" if whatsapp else "📱 Cadastrar WhatsApp"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=whatsapp_text, callback_data="alterar_whatsapp")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="menu_profile")]
    ])


def recharge_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de recarga.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💠 Pix Rápido", callback_data="recarga_pix")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")]
    ])


def affiliate_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado do menu de afiliados.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Solicitar Saque", callback_data="solicitar_saque")],
        [InlineKeyboardButton(text="📊 Histórico de Saques", callback_data="historico_saques")],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")]
    ])


def rankings_keyboard(active_tab: str = "servicos") -> InlineKeyboardMarkup:
    """
    Teclado de rankings com abas.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅" if active_tab == "servicos" else "☑️",
                callback_data="ranking_servicos"
            ),
            InlineKeyboardButton(
                text="✅" if active_tab == "recargas" else "☑️",
                callback_data="ranking_recargas"
            ),
            InlineKeyboardButton(
                text="✅" if active_tab == "saldo" else "☑️",
                callback_data="ranking_saldo"
            ),
            InlineKeyboardButton(
                text="✅" if active_tab == "compras" else "☑️",
                callback_data="ranking_compras"
            )
        ],
        [InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def alerts_keyboard(produtos: list, pagina: int = 0, total_paginas: int = 1) -> InlineKeyboardMarkup:
    """
    Teclado de alertas com lista de produtos.
    `produtos`: lista de {id, nome, alerta_ativo}
    """
    buttons = []
    for prod in produtos:
        status = "✅" if prod.get("alerta_ativo") else "❌"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {prod['nome']}",
                callback_data=f"alerta:{prod['id']}"
            )
        ])
    # Paginação simplificada
    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"alerta_pag:{pagina-1}"))
    if pagina < total_paginas - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"alerta_pag:{pagina+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⏮️ Voltar", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def recharge_value_received_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado exibido enquanto aguarda o valor da recarga (apenas cancelar).
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_recarga")]
    ])
