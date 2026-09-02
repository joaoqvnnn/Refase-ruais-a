import re


def only_digits(value: str) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def is_valid_cpf(cpf: str) -> bool:
    cpf = only_digits(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digito = ((10 * soma) % 11) % 10
        if int(cpf[i]) != digito:
            return False
    return True


def is_valid_phone_br(phone: str) -> bool:
    d = only_digits(phone)
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    # 10 ou 11 dígitos (fix + número)
    return len(d) in (10, 11)


def normalize_phone_br(phone: str) -> str:
    d = only_digits(phone)
    if not d.startswith("55"):
        d = "55" + d
    return d


def is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def detect_pix_key_type(key: str) -> str | None:
    """Retorna: cpf | phone | email | random | None se inválido."""
    key = (key or "").strip()
    if not key:
        return None
    digits = only_digits(key)
    if "@" in key and is_valid_email(key):
        return "email"
    if len(digits) == 11 and is_valid_cpf(digits):
        return "cpf"
    if is_valid_phone_br(key):
        return "phone"
    # chave aleatória UUID-like
    cleaned = key.replace("-", "")
    if len(cleaned) >= 32:
        return "random"
    return None


def format_cpf(cpf: str) -> str:
    d = only_digits(cpf)
    if len(d) != 11:
        return cpf
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
