# ==============================================
# LARIZINHA STORE - SERVIÇO DE NOTIFICAÇÕES (EMAIL/WHATSAPP)
# ==============================================

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM,
    SMTP_TLS,
    WHATSAPP_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
)

logger = logging.getLogger(__name__)


async def send_email(destinatario: str, assunto: str, corpo: str) -> bool:
    """
    Envia um email simples via SMTP.
    Retorna True se enviou com sucesso.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP não configurado. Email não enviado.")
        return False

    try:
        import aiosmtplib

        mensagem = MIMEMultipart()
        mensagem["From"] = SMTP_FROM or SMTP_USER
        mensagem["To"] = destinatario
        mensagem["Subject"] = assunto
        mensagem.attach(MIMEText(corpo, "plain", "utf-8"))

        await aiosmtplib.send(
            mensagem,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=SMTP_TLS,
        )
        logger.info(f"Email enviado para {destinatario}")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar email: {e}")
        return False


async def send_whatsapp(numero: str, mensagem: str) -> bool:
    """
    Envia mensagem via WhatsApp Business API.
    Retorna True se enviou com sucesso.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp API não configurada. Mensagem não enviada.")
        return False

    try:
        import aiohttp

        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": mensagem},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    logger.info(f"WhatsApp enviado para {numero}")
                    return True
                else:
                    logger.error(f"Falha WhatsApp: {resp.status} {await resp.text()}")
                    return False
    except Exception as e:
        logger.error(f"Exceção ao enviar WhatsApp: {e}")
        return False


async def send_broadcast(user_ids: list[int], texto: str) -> dict:
    """
    Envia uma mensagem para uma lista de IDs via bot.
    Retorna dict com totais de sucessos e falhas.
    """
    from aiogram import Bot
    from config import TELEGRAM_TOKEN

    bot = Bot(token=TELEGRAM_TOKEN)
    enviados = 0
    falhas = 0

    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=texto)
            enviados += 1
        except Exception as e:
            logger.warning(f"Falha ao enviar broadcast para {uid}: {e}")
            falhas += 1

    await bot.session.close()
    return {"total": len(user_ids), "enviados": enviados, "falhas": falhas}
