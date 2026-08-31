# ==============================================
# LARIZINHA STORE - TEXTOS PADRÃO DO ADMIN
# ==============================================

# Mensagens usadas no painel administrativo quando não houver
# necessidade de interação dinâmica complexa.

DEFAULT_ADMIN_TEXTS = {
    "admin_welcome": (
        "🔧 PAINEL ADMINISTRATIVO\n\n"
        "Bem-vindo, {admin_name}.\n"
        "Selecione uma opção abaixo para gerenciar o bot."
    ),
    "admin_access_denied": (
        "⛔ Acesso negado.\n"
        "Você não tem permissão para acessar o painel administrativo."
    ),
    "admin_operation_cancelled": (
        "Operação cancelada."
    ),
    "admin_product_created": (
        "✅ Produto criado com sucesso!\n"
        "ID: {product_id}\n"
        "Nome: {product_name}"
    ),
    "admin_product_updated": (
        "✅ Produto atualizado com sucesso!"
    ),
    "admin_product_deleted": (
        "✅ Produto removido."
    ),
    "admin_stock_added": (
        "✅ {quantidade} item(ns) adicionado(s) ao estoque do produto #{produto_id}."
    ),
    "admin_category_created": (
        "✅ Categoria criada com sucesso!\nID: {category_id}\nNome: {category_name}"
    ),
    "admin_category_updated": (
        "✅ Categoria atualizada."
    ),
    "admin_category_deleted": (
        "✅ Categoria removida."
    ),
    "admin_giftcards_generated": (
        "✅ {quantidade} gift card(s) gerado(s) com sucesso.\n"
        "Valor: R$ {valor}\n"
        "Códigos:\n{codigos}"
    ),
    "admin_giftcard_revoked": (
        "✅ Gift card revogado."
    ),
    "admin_affiliate_commission_updated": (
        "✅ Comissão do afiliado atualizada para {comissao}%."
    ),
    "admin_withdrawal_approved": (
        "✅ Saque aprovado."
    ),
    "admin_withdrawal_rejected": (
        "✅ Saque recusado. Valor devolvido ao saldo do afiliado."
    ),
    "admin_payment_forced": (
        "✅ Pagamento aprovado manualmente."
    ),
    "admin_payment_cancelled": (
        "✅ Pagamento cancelado."
    ),
    "admin_broadcast_sent": (
        "✅ Broadcast concluído.\nTotal: {total}\nEnviados: {enviados}\nFalhas: {falhas}"
    ),
    "admin_setting_updated": (
        "✅ Configuração '{descricao}' atualizada para: {novo_valor}"
    ),
}


def get_admin_message(key: str, **kwargs) -> str:
    """
    Retorna a mensagem padrão do admin formatada com os argumentos.
    Se a chave não existir, retorna string vazia.
    """
    texto = DEFAULT_ADMIN_TEXTS.get(key, "")
    if texto and kwargs:
        try:
            return texto.format(**kwargs)
        except KeyError:
            return texto
    return texto
