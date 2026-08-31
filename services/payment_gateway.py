# ==============================================
# LARIZINHA STORE - SERVIÇO DE GATEWAY DE PAGAMENTO
# ==============================================

import logging
import base64
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import mercadopago

from config import (
    MP_ACCESS_TOKEN,
    MP_SANDBOX,
    WEBHOOK_URL,
    PIX_EXPIRATION_MINUTES,
)

logger = logging.getLogger(__name__)

# Inicializa o SDK do Mercado Pago se token disponível
if MP_ACCESS_TOKEN:
    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
else:
    sdk = None
    logger.warning("MP_ACCESS_TOKEN não configurado. Gateway de pagamento indisponível.")


async def create_pix_payment(valor: float, user_id: int, description: str = "Recarga Larizinha Store") -> dict:
    """
    Cria uma cobrança PIX no Mercado Pago e retorna os dados.
    Em caso de falha ou ausência de token, retorna um pagamento simulado (para testes).
    O retorno inclui 'qr_code_base64' para envio da imagem.
    """
    valor_decimal = Decimal(str(valor)).quantize(Decimal("0.01"))
    expiration = datetime.now() + timedelta(minutes=PIX_EXPIRATION_MINUTES)

    payment_data = {
        "transaction_amount": float(valor_decimal),
        "description": description,
        "payment_method_id": "pix",
        "payer": {
            "email": f"{user_id}@telegram.com",
            "first_name": "Cliente",
            "last_name": "",
        },
        "notification_url": WEBHOOK_URL if WEBHOOK_URL else None,
        "date_of_expiration": expiration.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }

    # Tenta criar cobrança real no Mercado Pago
    if sdk and not MP_SANDBOX:
        try:
            result = sdk.payment().create(payment_data)
            response = result.get("response", {})
            if result.get("status") == 201:
                point_of_interaction = response.get("point_of_interaction", {}).get("transaction_data", {})
                qr_code_base64 = point_of_interaction.get("qr_code_base64")
                return {
                    "codigo_pix": point_of_interaction.get("qr_code"),
                    "qr_code_base64": qr_code_base64,
                    "txid": str(response.get("id")),
                    "data_expiracao": expiration,
                    "status": "pendente",
                }
            else:
                logger.error(f"Erro ao criar PIX no Mercado Pago: {result}")
        except Exception as e:
            logger.exception("Exceção ao criar PIX no Mercado Pago")

    # Fallback simulado (apenas para desenvolvimento/testes)
    logger.info("Usando simulação de PIX (fallback).")
    codigo_pix = "00020101021226830014BR.GOV.BCB.PIX2561qrcodespix.sejaefi.com.br/v2/" + uuid.uuid4().hex
    # Simula um QR code mínimo (não é válido, apenas placeholder)
    qr_code_base64 = base64.b64encode(codigo_pix.encode()).decode()
    return {
        "codigo_pix": codigo_pix,
        "qr_code_base64": qr_code_base64,
        "txid": None,
        "data_expiracao": expiration,
        "status": "pendente",
    }


async def check_payment_status(payment_id: str) -> str:
    """
    Consulta o status de um pagamento no Mercado Pago.
    Retorna 'pago', 'pendente', 'expirado', 'cancelado' ou 'desconhecido'.
    """
    if sdk and not MP_SANDBOX and payment_id:
        try:
            result = sdk.payment().get(payment_id)
            response = result.get("response", {})
            status = response.get("status")
            if status == "approved":
                return "pago"
            elif status in ("pending", "in_process"):
                return "pendente"
            elif status in ("cancelled", "rejected"):
                return "cancelado"
            elif status == "expired":
                return "expirado"
        except Exception as e:
            logger.exception("Exceção ao consultar pagamento no Mercado Pago")
    return "pendente"


async def expire_pending_payments():
    """
    Marca como expirados todos os pagamentos pendentes cuja data de expiração passou.
    Deve ser chamada periodicamente via Celery.
    """
    from database.connection import async_session
    from database.models import PagamentoPix
    from sqlalchemy import update

    agora = datetime.now()
    async with async_session() as session:
        await session.execute(
            update(PagamentoPix)
            .where(PagamentoPix.status == "pendente", PagamentoPix.data_expiracao < agora)
            .values(status="expirado")
        )
        await session.commit()
        logger.info("Pagamentos expirados atualizados.")


async def verify_pending_payments():
    """
    Consulta o gateway para verificar pagamentos pendentes.
    Deve ser chamada periodicamente via Celery.
    """
    from database.connection import async_session
    from database.models import PagamentoPix, User, Log
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(
            select(PagamentoPix).where(PagamentoPix.status == "pendente")
        )
        pagamentos = result.scalars().all()

        for pagamento in pagamentos:
            if pagamento.data_expiracao and datetime.now() > pagamento.data_expiracao:
                pagamento.status = "expirado"
                continue

            if pagamento.txid:
                status = await check_payment_status(pagamento.txid)
            else:
                # Sem txid, se gateway real não estiver ativo, permanece pendente
                continue

            if status == "pago":
                pagamento.status = "pago"
                pagamento.data_pagamento = datetime.now()

                if pagamento.tipo == "recarga":
                    user = await session.get(User, pagamento.user_id)
                    if user:
                        user.saldo += pagamento.valor + pagamento.bonus
                        user.total_recargas += pagamento.valor

                log = Log(
                    user_id=pagamento.user_id,
                    acao="pagamento_confirmado",
                    detalhes={"payment_id": str(pagamento.id), "tipo": pagamento.tipo}
                )
                session.add(log)
            elif status == "expirado":
                pagamento.status = "expirado"
            elif status == "cancelado":
                pagamento.status = "cancelado"

        await session.commit()


async def process_webhook_notification(payment_id: str) -> bool:
    """
    Processa notificação de webhook do Mercado Pago.
    Recebe o ID do pagamento e verifica o status, atualizando o banco.
    Retorna True se o pagamento foi aprovado.
    """
    status = await check_payment_status(payment_id)

    async with async_session() as session:
        from database.models import PagamentoPix, User, Log
        from sqlalchemy import select

        result = await session.execute(
            select(PagamentoPix).where(PagamentoPix.txid == str(payment_id))
        )
        pagamento = result.scalar_one_or_none()
        if not pagamento:
            logger.warning(f"Webhook: pagamento {payment_id} não encontrado.")
            return False

        if status == "pago" and pagamento.status != "pago":
            pagamento.status = "pago"
            pagamento.data_pagamento = datetime.now()

            if pagamento.tipo == "recarga":
                user = await session.get(User, pagamento.user_id)
                if user:
                    user.saldo += pagamento.valor + pagamento.bonus
                    user.total_recargas += pagamento.valor

            log = Log(
                user_id=pagamento.user_id,
                acao="pagamento_confirmado_webhook",
                detalhes={"payment_id": str(pagamento.id)}
            )
            session.add(log)
            await session.commit()
            logger.info(f"Webhook: pagamento {pagamento.id} confirmado.")
            return True
        elif status in ("expirado", "cancelado"):
            if pagamento.status == "pendente":
                pagamento.status = status
                await session.commit()
                logger.info(f"Webhook: pagamento {pagamento.id} {status}.")
        return False
