# ==============================================
# LARIZINHA STORE - VALIDAÇÕES DE ENTRADA
# ==============================================

import re
from decimal import Decimal, InvalidOperation


def validar_email(email: str) -> bool:
    """
    Verifica se o email possui um formato válido.
    """
    if not email:
        return False
    padrao = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(padrao, email) is not None


def validar_telefone(telefone: str) -> bool:
    """
    Valida número de telefone (aceita formatos com ou sem máscara).
    Mínimo de 10 dígitos (DDD + número).
    """
    digitos = re.sub(r"\D", "", telefone)
    return len(digitos) >= 10


def validar_valor_minimo(valor: str | float | Decimal, minimo: float | Decimal) -> bool:
    """
    Verifica se um valor é maior ou igual ao mínimo.
    """
    try:
        valor_decimal = Decimal(str(valor))
        minimo_decimal = Decimal(str(minimo))
        return valor_decimal >= minimo_decimal
    except (InvalidOperation, ValueError):
        return False


def validar_valor_positivo(valor: str | float | Decimal) -> bool:
    """
    Verifica se o valor é um número positivo.
    """
    try:
        return Decimal(str(valor)) > 0
    except (InvalidOperation, ValueError):
        return False


def validar_quantidade(quantidade: str) -> bool:
    """
    Verifica se a quantidade é um inteiro positivo.
    """
    if not quantidade:
        return False
    try:
        qtd = int(quantidade)
        return qtd > 0
    except ValueError:
        return False


def validar_codigo_giftcard(codigo: str) -> bool:
    """
    Valida o formato de um código de gift card.
    Aceita letras maiúsculas, números e hífen/underscore, tamanho 6 a 64.
    """
    if not codigo:
        return False
    padrao = r"^[A-Z0-9\-_]{6,64}$"
    return re.match(padrao, codigo) is not None


def validar_chave_pix(chave: str) -> bool:
    """
    Valida chave PIX (email, telefone, CPF/CNPJ ou chave aleatória).
    """
    if not chave:
        return False

    chave_limpa = chave.strip()

    # Email
    if validar_email(chave_limpa):
        return True

    # Telefone (pelo menos 10 dígitos)
    if validar_telefone(chave_limpa):
        return True

    # CPF/CNPJ (somente dígitos)
    digitos = re.sub(r"\D", "", chave_limpa)
    if len(digitos) in (11, 14):
        return True

    # Chave aleatória (UUID)
    padrao_uuid = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    if re.match(padrao_uuid, chave_limpa):
        return True

    return False


def validar_nome_produto(nome: str) -> bool:
    """
    Valida nome de produto: entre 2 e 255 caracteres.
    """
    return 2 <= len(nome.strip()) <= 255


def validar_preco(valor: str | float | Decimal) -> bool:
    """
    Verifica se o preço é um número positivo (maior que zero).
    """
    return validar_valor_positivo(valor)


def validar_estoque(valor: str | int) -> bool:
    """
    Valida estoque: inteiro não negativo.
    """
    try:
        return int(valor) >= 0
    except (ValueError, TypeError):
        return False


def validar_porcentagem(valor: str | float | Decimal) -> bool:
    """
    Valida percentual entre 0 e 100.
    """
    try:
        percent = Decimal(str(valor))
        return Decimal("0") <= percent <= Decimal("100")
    except (InvalidOperation, ValueError):
        return False


def validar_id_telegram(valor: str | int) -> bool:
    """
    Valida se é um ID de Telegram (inteiro positivo).
    """
    try:
        return int(valor) > 0
    except (ValueError, TypeError):
        return False
