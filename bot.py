# ==============================================
# LARIZINHA STORE - INICIALIZAÇÃO DO BOT
# ==============================================

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para facilitar imports
sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TELEGRAM_TOKEN, ADMIN_IDS, LOG_LEVEL
from utils.logger import setup_logger

# Configuração de logging
logger = setup_logger("bot", LOG_LEVEL)

# Importação dos routers (serão criados nos próximos arquivos)
# Se algum módulo ainda não existir, comente temporariamente
from handlers.client.start import router as client_start_router
from handlers.client.catalog import router as client_catalog_router
from handlers.client.product import router as client_product_router
from handlers.client.purchase import router as client_purchase_router
from handlers.client.payment import router as client_payment_router
from handlers.client.profile import router as client_profile_router
from handlers.client.history import router as client_history_router
from handlers.client.giftcard import router as client_giftcard_router
from handlers.client.recharge import router as client_recharge_router
from handlers.client.affiliate import router as client_affiliate_router
from handlers.client.rankings import router as client_rankings_router
from handlers.client.alerts import router as client_alerts_router
from handlers.client.search import router as client_search_router
from handlers.client.special_commands import router as client_special_commands_router
from handlers.client.inline import router as client_inline_router

from handlers.admin.panel import router as admin_panel_router
from handlers.admin.products import router as admin_products_router
from handlers.admin.categories import router as admin_categories_router
from handlers.admin.messages import router as admin_messages_router
from handlers.admin.users import router as admin_users_router
from handlers.admin.giftcards import router as admin_giftcards_router
from handlers.admin.affiliates import router as admin_affiliates_router
from handlers.admin.payments import router as admin_payments_router
from handlers.admin.statistics import router as admin_statistics_router
from handlers.admin.broadcast import router as admin_broadcast_router
from handlers.admin.logs import router as admin_logs_router
from handlers.admin.settings import router as admin_settings_router

async def main() -> None:
    """
    Função principal que inicializa o bot e o dispatcher.
    """
    logger.info("Iniciando Larizinha Store Bot...")

    # Inicializa o bot com token e parse mode padrão HTML
    bot = Bot(
        token=TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Usando MemoryStorage para FSM (em produção, trocar por RedisStorage)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Inclui todos os routers do cliente
    dp.include_router(client_start_router)
    dp.include_router(client_catalog_router)
    dp.include_router(client_product_router)
    dp.include_router(client_purchase_router)
    dp.include_router(client_payment_router)
    dp.include_router(client_profile_router)
    dp.include_router(client_history_router)
    dp.include_router(client_giftcard_router)
    dp.include_router(client_recharge_router)
    dp.include_router(client_affiliate_router)
    dp.include_router(client_rankings_router)
    dp.include_router(client_alerts_router)
    dp.include_router(client_search_router)
    dp.include_router(client_special_commands_router)
    dp.include_router(client_inline_router)

    # Inclui todos os routers do admin
    dp.include_router(admin_panel_router)
    dp.include_router(admin_products_router)
    dp.include_router(admin_categories_router)
    dp.include_router(admin_messages_router)
    dp.include_router(admin_users_router)
    dp.include_router(admin_giftcards_router)
    dp.include_router(admin_affiliates_router)
    dp.include_router(admin_payments_router)
    dp.include_router(admin_statistics_router)
    dp.include_router(admin_broadcast_router)
    dp.include_router(admin_logs_router)
    dp.include_router(admin_settings_router)

    logger.info("Routers registrados com sucesso.")
    logger.info("Bot em execução... Pressione Ctrl+C para parar.")

    # Inicia o polling (para produção com webhook, substituir)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot encerrado.")
    except Exception as e:
        logger.exception(f"Erro fatal: {e}")
