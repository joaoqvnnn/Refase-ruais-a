# ==============================================
# LARIZINHA STORE - FUNÇÕES AUXILIARES
# ==============================================

import re
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal


def format_money(valor: Decimal | float | int) -> str:
    """
    Formata um valor numérico para o padrão de moeda brasileiro.

    Exemplo: 1234.5 -> "R$ 1.234,50"
    """
    valor = Decimal(str(valor))
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_date(data: datetime | date, formato: str = "%d/%m/%Y") -> str:
    """
    Formata uma data para o padrão brasileiro.
    """
    if isinstance(data, datetime):
        return data.strftime(formato)
    elif isinstance(data, date):
        return data.strftime(formato)
    return str(data)


def generate_uuid() -> str:
    """
    Gera um UUID v4 em formato string.
    """
    return str(uuid.uuid4())


def generate_reference(prefixo: str = "") -> str:
    """
    Gera uma referência única baseada em timestamp e hash curto.
    Útil para criar referências de pagamento legíveis.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    curto = uuid.uuid4().hex[:6].upper()
    return f"{prefixo}{timestamp}{curto}"


def mask_email(email: str) -> str:
    """
    Mascara parcialmente um email para exibição segura.

    Exemplo: joao.silva@gmail.com -> j***o@***.com
    """
    if not email or "@" not in email:
        return email
    usuario, dominio = email.split("@", 1)
    if len(usuario) <= 2:
        usuario_mascarado = usuario[0] + "*" * max(len(usuario)-1, 1)
    else:
        usuario_mascarado = usuario[0] + "*" * (len(usuario)-2) + usuario[-1]
    return f"{usuario_mascarado}@{dominio}"


def mask_phone(phone: str) -> str:
    """
    Mascara um número de telefone, mantendo apenas os últimos 4 dígitos visíveis.
    """
    digitos = re.sub(r"\D", "", phone)
    if len(digitos) <= 4:
        return phone
    return f"{'*' * (len(digitos)-4)}{digitos[-4:]}"


def calcular_vencimento(garantia_dias: int) -> date:
    """
    Calcula a data de vencimento a partir da garantia em dias.
    """
    return date.today() + timedelta(days=garantia_dias)


def calcular_bonus(valor: Decimal | float, percentual: Decimal | float) -> Decimal:
    """
    Calcula o bônus sobre um valor.
    """
    valor = Decimal(str(valor))
    percentual = Decimal(str(percentual))
    return (valor * percentual / Decimal("100")).quantize(Decimal("0.01"))


def format_telegram_id(user_id: int) -> str:
    """
    Formata o ID do Telegram para exibição.
    """
    return str(user_id)


def parse_int(texto: str) -> int | None:
    """
    Converte uma string para inteiro, retornando None se inválido.
    """
    try:
        return int(texto.strip())
    except (ValueError, TypeError):
        return None


def parse_float(texto: str) -> float | None:
    """
    Converte uma string para float, tratando vírgula como separador decimal.
    """
    if not texto:
        return None
    texto_limpo = texto.strip().replace(",", ".")
    try:
        return float(texto_limpo)
    except ValueError:
        return None


def format_short_date(data: datetime) -> str:
    """
    Formata data e hora curta: DD/MM/YYYY HH:MM
    """
    return data.strftime("%d/%m/%Y %H:%M")


def truncate_text(texto: str, limite: int = 100) -> str:
    """
    Corta um texto no limite especificado, adicionando reticências.
    """
    if len(texto) <= limite:
        return texto
    return texto[:limite-3] + "..."
