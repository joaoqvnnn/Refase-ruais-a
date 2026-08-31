# ==============================================
# LARIZINHA STORE - CONFIGURAÇÕES GERAIS
# ==============================================

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent

# ---------- TELEGRAM ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Converte a string "123,456" em lista de inteiros [123, 456]
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip()]

BOT_USERNAME = os.getenv("BOT_USERNAME", "larizinhastorebot")

# ---------- BANCO DE DADOS (PostgreSQL) ----------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "larizinhastore")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# URL SQLAlchemy (usada pelo asyncpg)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------- REDIS ----------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# ---------- MERCADO PAGO ----------
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY", "")
MP_SANDBOX = os.getenv("MP_SANDBOX", "true").lower() == "true"

# ---------- WEBHOOK ----------
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

# ---------- CONFIGURAÇÕES DE PAGAMENTO ----------
PIX_EXPIRATION_MINUTES = int(os.getenv("PIX_EXPIRATION_MINUTES", "10"))
MIN_RECHARGE_VALUE = float(os.getenv("MIN_RECHARGE_VALUE", "4.00"))
RECHARGE_BONUS_PERCENT = float(os.getenv("RECHARGE_BONUS_PERCENT", "10"))
MIN_BONUS_VALUE = float(os.getenv("MIN_BONUS_VALUE", "10.00"))

# ---------- AFILIADOS ----------
DEFAULT_AFFILIATE_COMMISSION = float(os.getenv("DEFAULT_AFFILIATE_COMMISSION", "10"))
MIN_WITHDRAWAL_VALUE = float(os.getenv("MIN_WITHDRAWAL_VALUE", "20.00"))

# ---------- ANTI-FLOOD ----------
FLOOD_MAX_MESSAGES_PER_MINUTE = int(os.getenv("FLOOD_MAX_MESSAGES_PER_MINUTE", "5"))
FLOOD_BLOCK_SECONDS = int(os.getenv("FLOOD_BLOCK_SECONDS", "60"))

# ---------- LOGGING ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# ---------- EMAIL (SMTP) ----------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"

# ---------- WHATSAPP BUSINESS API ----------
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

# ---------- MANUTENÇÃO ----------
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

# ---------- TIMEZONE ----------
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

# ==============================================
# VALIDAÇÕES BÁSICAS
# ==============================================
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não configurado no arquivo .env")

if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS não configurado no arquivo .env")

if not MP_ACCESS_TOKEN:
    print("AVISO: MP_ACCESS_TOKEN não configurado. Pagamentos PIX não funcionarão.")

if not DB_PASSWORD:
    print("AVISO: DB_PASSWORD não configurado. Conexão com banco pode falhar.")

# ==============================================
# CONFIGURAÇÃO DE LOGGING
# ==============================================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
