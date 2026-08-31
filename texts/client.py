# ==============================================
# LARIZINHA STORE - TEXTOS PADRÃO DO CLIENTE
# ==============================================

# Esses textos são usados como fallback quando a mensagem
# personalizada não está definida no banco de dados.

DEFAULT_TEXTS = {
    # ----- /start e menu principal -----
    "start": (
        "🎬 Bem-vindo à {NOME_BOT}! ✨\n"
        "A sua central de produtos digitais com entrega 100% automática.\n\n"
        "Pagou, recebeu. Sem filas, sem precisar falar com atendente, 24 horas por dia! ⚡️\n\n"
        "🛡 Segurança e Suporte:\n"
        "Mais de 12.000 clientes já passaram por aqui.\n"
        "Participe da nossa comunidade e veja as referências\n\n"
        "💠 Seus Dados:\n"
        "├👤 ID: {user_id}\n"
        "└💰 Saldo Atual: R$ {saldo}\n\n"
        "👇 COMO COMEÇAR:\n"
        "Clique no botão \"🛍 Comprar Produtos\" abaixo para ver nosso catálogo e escolher seu produto!"
    ),

    # ----- Catálogo -----
    "catalogo": (
        "📱 {NOME_BOT} | Catálogo de Serviços\n"
        "🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗\n\n"
        "💰| Saldo da Carteira: R$ {saldo}\n\n"
        "⬇️ Selecione uma categoria abaixo para ver nossos planos:"
    ),

    "categoria_produtos": (
        "📱 {NOME_BOT} | {categoria_nome}\n"
        "🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗\n\n"
        "💰| Saldo da Carteira: R$ {saldo}\n\n"
        "⬇️ Selecione um produto abaixo:"
    ),

    # ----- Detalhes do produto -----
    "produto_detalhes": (
        "🔥 OPORTUNIDADE EXCLUSIVA 🔥\n"
        "🚀 {nome_produto}\n\n"
        "🟢 DISPONÍVEL AGORA\n"
        "├ 💵 Preço: R$ {preco}\n"
        "├ 💰 Seu Saldo: R$ {saldo}\n"
        "└ 📦 Estoque: {estoque}\n\n"
        "📝 Descrição:\n"
        "{descricao}\n\n"
        "📊 Estatísticas em tempo real:\n"
        "⚡️ Já foram vendidas {vendidos} unidades!\n"
        "👀 {visualizacoes} pessoas estão vendo isso agora.\n\n"
        "🛡 Garantia: {garantia_dias} dias\n"
        "✅ Compra segura. Ao adquirir, concorda com /termos"
    ),

    # ----- Saldo insuficiente -----
    "saldo_insuficiente": (
        "❌ Saldo insuficiente!\n\n"
        "💰 Seu saldo: R$ {saldo}\n"
        "💵 Valor do produto: R$ {preco}\n"
        "📉 Faltam: R$ {faltam}\n\n"
        "💡 Deseja gerar um PIX no valor de R$ {preco} para completar a compra?"
    ),

    "saldo_insuficiente_multi": (
        "❌ Saldo insuficiente!\n\n"
        "💰 Seu saldo: R$ {saldo}\n"
        "💵 Valor total: R$ {total}\n"
        "📉 Faltam: R$ {faltam}\n\n"
        "💡 Deseja gerar um PIX para completar a compra?"
    ),

    # ----- Geração de PIX -----
    "pix_gerado": (
        "⏳ Gerando pagamento...\n"
        "💰 Comprar Saldo com Pix Automático:\n\n"
        "⏱️ Expira em: {minutos} Minutos  \n"
        "💵 Valor: R$ {valor}  \n"
        "✨ ID da Recarga: {payment_id}\n\n"
        "📃 Atenção: Este código é válido para apenas um único pagamento.  \n"
        "Se você utilizá-lo mais de uma vez, o saldo adicional será perdido sem direito a reembolso.\n\n"
        "💎 Pix Copia e Cola:  \n"
        "{codigo_pix}\n\n"
        "💡 Dica: Clique no código acima para copiar.  \n\n"
        "📊 Dados:\n"
        "— 💰 Saldo Atual: R$ {saldo}\n"
        "— 🎁 Bônus à receber: R$ {bonus}\n"
        "— 💸 Saldo após o pagamento: R$ {saldo_apos}\n\n"
        "🇧🇷 Após o pagamento, seu saldo será liberado instantaneamente."
    ),

    # ----- Pagamento não identificado -----
    "pagamento_nao_identificado": (
        "🔄 Aguardando pagamento...\n\n"
        "Ainda não identificamos o pagamento do seu PIX.\n"
        "Se você já realizou, aguarde alguns instantes e tente novamente.\n\n"
        "💡 O PIX é instantâneo e a liberação é automática!"
    ),

    # ----- Pagamento expirado -----
    "pagamento_expirado": (
        "⌛️ PAGAMENTO PIX EXPIRADO\n\n"
        "⚠️ O tempo limite para realizar este pagamento foi excedido.  \n\n"
        "🆔 Referência do Pagamento: {payment_id}  \n"
        "💸 Valor Solicitado: R$ {valor}"
    ),

    # ----- Compra aprovada/entrega -----
    "compra_aprovada": (
        "🎉 COMPRA APROVADA!\n\n"
        "🚀 Produto: {produto}\n"
        "💰 Valor: R$ {valor}\n"
        "📅 Data: {data}\n"
        "⏰ Hora: {hora}\n"
        "💳 Pagamento: {forma_pagamento}\n"
        "🆔 Pedido: {order_id}\n\n"
        "Entrega:\n"
        "{conteudo}"
    ),

    # ----- Perfil -----
    "perfil": (
        "👤 Meu perfil\n\n"
        "🔍 Veja aqui os detalhes da sua conta:\n\n"
        "- 👤 Informações:\n"
        "🆔 ID da Carteira: {user_id}\n"
        "💰 Saldo Atual: R$ {saldo}\n"
        "📲 Seu Whatsapp: {whatsapp}\n\n"
        "─── 📊 Suas Movimentações:\n"
        "ー 🛒 Compras Realizadas: {total_compras}\n"
        "ー 💰 Total Gasto Em Compras: R$ {total_gasto}\n"
        "ー 💠 Pix Inseridos: R$ {total_recargas}\n"
        "ー 🎁 Gifts Resgatados: R$ {total_gifts}"
    ),

    # ----- Histórico vazio -----
    "historico_vazio": (
        "Você não tem compras ativas (não vencidas) no bot.\n\n"
        "Use o botão abaixo para ver todas as compras."
    ),

    "historico_vazio_todas": (
        "Você ainda não realizou nenhuma compra."
    ),

    # ----- Histórico item -----
    "historico_item": (
        "🛍 Compras: {indice}/{total}\n\n"
        "⏰ Data da compra: {data}\n"
        "📆 Vencimento: {vencimento}\n"
        "💰 Valor: R$ {valor}\n"
        "🎫 ID da compra: {id}\n"
        "⚜️ Serviço: {nome_produto}\n"
        "📧 Email: {email}\n"
        "🔐 Senha: {senha}\n"
        "📃 Nota: {nota}\n\n"
        "Ref: {referencia}"
    ),

    # ----- Gift card -----
    "giftcard": (
        "🎁 RESGATAR GIFT CARD\n\n"
        "Digite o código do seu gift card abaixo:\n\n"
        "Exemplo: ABC123XYZ456"
    ),

    "giftcard_sucesso": (
        "🎉 Gift Card resgatado com sucesso!\n\n"
        "💰 Valor adicionado: R$ {valor}\n"
        "💠 Saldo atual: R$ {saldo}"
    ),

    "giftcard_erro": (
        "❌ Gift não encontrado.\n\n"
        "Verifique o código e tente novamente."
    ),

    # ----- Alterar dados -----
    "alterar_dados": (
        "✏️ Alterar Dados\n\n"
        "Selecione o dado que deseja alterar:\n\n"
        "📱 WhatsApp: {whatsapp}"
    ),

    "alterar_whatsapp_digitar": (
        "📱 Digite seu novo número de WhatsApp:\n\n"
        "Exemplo: 449986915568"
    ),

    # ----- Recarga -----
    "recarga_inicio": (
        "🆔| ID da Carteira: {user_id}\n"
        "💰| Saldo Disponível: R$ {saldo}\n\n"
        "📍 Opte por 💠 Pix Rápido para que seu saldo seja creditado imediatamente.\n\n"
        "💡 Selecione uma opção para recarregar:"
    ),

    "recarga_valor": (
        "ℹ️ Informe o valor que deseja recarregar:\n\n"
        "🔻 Recarga mínima: R$ {minimo}\n\n"
        "⚠️ Por favor, envie o valor que deseja recarregar agora.\n"
        "Ao realizar um depósito você declara ter lido e estar de acordo com nossos /termos\n\n"
        "🎁 Bônus de recarga: {bonus_percent}%\n"
        "❗️ Recarga mínima para ganhar o bônus: R$ {minimo_bonus}"
    ),

    # ----- Afiliados -----
    "afiliados": (
        "💰 PROGRAMA DE AFILIADOS\n\n"
        "⚙️ Status: Ativo\n"
        "🧲 Sua comissão: {comissao}% (de todas recargas do indicado)\n\n"
        "👥 Indicações: {indicacoes}\n"
        "🪙 Total ganho: R$ {total_ganho}\n"
        "📊 Média: R$ {media}\n"
        "💰 Saque mínimo: R$ {saque_minimo}\n\n"
        "🔥 Saldo de comissões: R$ {saldo_comissoes}\n\n"
        "🌱| Nível: {nivel}\n"
        "🎯 Próxima meta: {meta} ({restantes} restantes)\n\n"
        "ℹ️ INFO: Seus indicados continuarão gerando comissão para sempre.\n"
        "A comissão pode ser alterada a qualquer momento, fique atento aos avisos.\n"
        "🔗 Seu link:\n"
        "{link}"
    ),

    "saque_historico_vazio": (
        "📊 HISTÓRICO DE SAQUES\n\n"
        "Você ainda não solicitou nenhum saque.\n\n"
        "📉 Saque mínimo atual: R$ {saque_minimo}"
    ),

    # ----- Rankings -----
    "rankings": (
        "🏆 Ranking dos serviços mais vendidos (deste mês)\n\n"
        "{lista}\n\n"
        "{mensagem_usuario}"
    ),

    # ----- Alertas -----
    "alerta": (
        "⚠️ Sistema de /alertas\n\n"
        "Seja notificado quando seu serviço favorito for abastecido 🤩\n"
        "🎯 Basta selecionar abaixo os serviços que você deseja ser notificado, e eu lhe avisarei sempre que for abastecido novas unidades.\n\n"
        "✅ Nossos produtos são de grandes demandas e acabam rápido, é importante que você seja notificado para aproveitar antes que acabe!\n\n"
        "Lista de serviços que você pode ser notificado ⤵️"
    ),

    # ----- Pesquisa inline -----
    "pesquisa": (
        "🎯 {nome_produto}\n"
        "💲 Valor: R$ {preco}\n"
        "📝 {descricao}\n\n"
        "Para comprar, clique no botão \"💳 Comprar\" abaixo ou abra o painel do serviço."
    ),

    # ----- Comandos especiais -----
    "comando_pix_uso": (
        "Você enviou em um formato incorreto. Envie /pix e o valor que deseja...\n"
        "Exemplo:\n"
        "/pix 10\n\n"
        "/pix 5.25"
    ),

    "comando_id": (
        "🆔 Seu id é: {user_id}"
    ),

    "comando_saldo": (
        "╭───────────────────╮\n"
        "💰 Carteira id: {user_id}\n"
        "💸 Saldo: R$ {saldo}\n"
        "╰───────────────────╯"
    ),

    # ----- Termos e suporte -----
    "termos": (
        "📋 Termos de Uso\n\n"
        "Ao utilizar este bot, você concorda com os termos e condições.\n"
        "Os produtos são digitais e não podem ser devolvidos após a entrega.\n"
        "Qualquer tentativa de fraude resultará em bloqueio permanente."
    ),

    "suporte": (
        "📞 Atendimento\n\n"
        "Entre em contato com nosso suporte:\n\n"
        "📱 WhatsApp: {whatsapp}\n"
        "📧 Email: {email}"
    ),

    "sobre": (
        "ℹ️ Sobre o Bot\n\n"
        "🤖 {NOME_BOT} - Versão 1.0\n"
        "Desenvolvido para vendas automáticas via Telegram.\n\n"
        "⚡ Entrega imediata\n"
        "💳 Pagamento via PIX\n"
        "🛡 Garantia de qualidade"
    ),
}


def get_message(key: str, **kwargs) -> str:
    """
    Retorna a mensagem padrão formatada com os argumentos fornecidos.
    Se a chave não existir, retorna uma string vazia.
    """
    texto = DEFAULT_TEXTS.get(key, "")
    if texto and kwargs:
        try:
            return texto.format(**kwargs)
        except KeyError as e:
            # Fallback se faltar alguma variável
            return texto
    return texto
