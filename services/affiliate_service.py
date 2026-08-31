# ==============================================
# LARIZINHA STORE - SERVIÇO DE AFILIADOS
# ==============================================

import logging
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session
from database.models import User, Afiliado, Log
from config import DEFAULT_AFFILIATE_COMMISSION

logger = logging.getLogger(__name__)


async def calcular_comissao(valor: Decimal, percentual: Decimal) -> Decimal:
    """
    Calcula o valor da comissão sobre um valor.
    """
    return (valor * percentual / Decimal("100")).quantize(Decimal("0.01"))


async def creditar_comissao_indicado(indicado_id: int, valor_recarga: Decimal) -> bool:
    """
    Credita comissão ao afiliado que indicou o usuário 'indicado_id',
    com base no valor da recarga realizada pelo indicado.
    Retorna True se comissão foi creditada, False caso contrário.
    """
    async with async_session() as session:
        # Busca o usuário indicado
        indicado = await session.get(User, indicado_id)
        if not indicado or not indicado.indicado_por:
            return False

        indicador_id = indicado.indicado_por

        # Busca o afiliado
        afiliado = await session.get(Afiliado, indicador_id)
        if not afiliado:
            # Cria registro se não existir
            afiliado = Afiliado(
                user_id=indicador_id,
                comissao_percent=Decimal(str(DEFAULT_AFFILIATE_COMMISSION)),
                total_ganho=Decimal("0.00"),
                saldo_comissoes=Decimal("0.00"),
                total_indicacoes=0,
                nivel="Iniciante",
                meta_indicacoes=5,
            )
            session.add(afiliado)
            await session.flush()

        # Calcula comissão
        comissao = await calcular_comissao(valor_recarga, afiliado.comissao_percent)

        # Atualiza valores
        afiliado.total_ganho += comissao
        afiliado.saldo_comissoes += comissao

        # Registra log
        log = Log(
            user_id=indicador_id,
            acao="comissao_afiliado",
            detalhes={
                "indicado_id": indicado_id,
                "valor_recarga": float(valor_recarga),
                "comissao": float(comissao),
            }
        )
        session.add(log)

        await session.commit()
        logger.info(f"Comissão de R$ {comissao} creditada para afiliado {indicador_id}")
        return True


async def incrementar_indicacoes(indicador_id: int) -> None:
    """
    Incrementa o contador de indicações de um afiliado e atualiza nível.
    Chamado quando um novo usuário entra com link de indicação.
    """
    async with async_session() as session:
        afiliado = await session.get(Afiliado, indicador_id)
        if not afiliado:
            afiliado = Afiliado(
                user_id=indicador_id,
                comissao_percent=Decimal(str(DEFAULT_AFFILIATE_COMMISSION)),
                total_ganho=Decimal("0.00"),
                saldo_comissoes=Decimal("0.00"),
                total_indicacoes=1,
                nivel="Iniciante",
                meta_indicacoes=5,
            )
            session.add(afiliado)
        else:
            afiliado.total_indicacoes += 1

        # Atualiza nível conforme meta
        if afiliado.total_indicacoes >= afiliado.meta_indicacoes:
            afiliado.nivel = "Avançado"
        elif afiliado.total_indicacoes >= (afiliado.meta_indicacoes // 2):
            afiliado.nivel = "Intermediário"

        await session.commit()


async def obter_dados_afiliado(user_id: int) -> dict:
    """
    Retorna os dados completos de um afiliado para exibição.
    Se não existir, cria registro padrão.
    """
    async with async_session() as session:
        afiliado = await session.get(Afiliado, user_id)
        if not afiliado:
            afiliado = Afiliado(
                user_id=user_id,
                comissao_percent=Decimal(str(DEFAULT_AFFILIATE_COMMISSION)),
                total_ganho=Decimal("0.00"),
                saldo_comissoes=Decimal("0.00"),
                total_indicacoes=0,
                nivel="Iniciante",
                meta_indicacoes=5,
            )
            session.add(afiliado)
            await session.commit()
            await session.refresh(afiliado)

        media = Decimal("0.00")
        if afiliado.total_indicacoes > 0:
            media = (afiliado.total_ganho / afiliado.total_indicacoes).quantize(Decimal("0.01"))

        restantes = max(0, afiliado.meta_indicacoes - afiliado.total_indicacoes)

        return {
            "comissao": float(afiliado.comissao_percent),
            "indicacoes": afiliado.total_indicacoes,
            "total_ganho": float(afiliado.total_ganho),
            "media": float(media),
            "saldo_comissoes": float(afiliado.saldo_comissoes),
            "nivel": afiliado.nivel,
            "meta": afiliado.meta_indicacoes,
            "restantes": restantes,
        }
