# ==============================================
# LARIZINHA STORE - SERVIDOR WEBHOOK MERCADO PAGO
# ==============================================

import logging
from aiohttp import web

from config import WEBHOOK_PORT, MP_ACCESS_TOKEN
from services.payment_gateway import process_webhook_notification
from utils.logger import setup_logger

logger = setup_logger("webhook", "INFO")


async def handle_mercadopago_webhook(request: web.Request) -> web.Response:
    """
    Recebe notificações do Mercado Pago e processa o pagamento.
    """
    try:
        data = await request.json()
        logger.info(f"Webhook recebido: {data}")

        # O Mercado Pago envia 'action' e 'data.id' ou 'type' e 'data.id'
        payment_id = None
        if "data" in data and "id" in data["data"]:
            payment_id = data["data"]["id"]
        elif "id" in data:
            payment_id = data["id"]

        if payment_id:
            aprovado = await process_webhook_notification(str(payment_id))
            if aprovado:
                logger.info(f"Pagamento {payment_id} confirmado via webhook.")
            return web.json_response({"status": "ok"})
        else:
            logger.warning("Webhook sem ID de pagamento.")
            return web.json_response({"status": "ignored"}, status=400)
    except Exception as e:
        logger.exception(f"Erro ao processar webhook: {e}")
        return web.json_response({"status": "error"}, status=500)


def create_app() -> web.Application:
    """
    Cria e configura a aplicação web.
    """
    app = web.Application()
    app.router.add_post("/webhook/mercadopago", handle_mercadopago_webhook)
    # Rota de teste
    app.router.add_get("/health", lambda request: web.json_response({"status": "alive"}))
    return app


if __name__ == "__main__":
    if not MP_ACCESS_TOKEN:
        logger.warning("MP_ACCESS_TOKEN não configurado. Webhook não iniciará corretamente.")
    logger.info(f"Iniciando servidor webhook na porta {WEBHOOK_PORT}...")
    web.run_app(create_app(), port=WEBHOOK_PORT)
