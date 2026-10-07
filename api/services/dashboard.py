from datetime import timedelta

from api.extensions import db
from api.models import (
    STATUS_VERIFICADO,
    Aditivo,
    AnaliseContrato,
    Contrato,
    ResultadoAnaliseClausula,
)
from api.utils import agora, numero_decimal


def _clausulas_alto_impacto(usuario):
    """Achados de alto impacto, sem descartados, usando o impacto corrigido se houver."""
    return (
        db.session.query(db.func.count(ResultadoAnaliseClausula.id))
        .join(AnaliseContrato)
        .join(Contrato)
        .filter(
            Contrato.usuario_id == usuario.id,
            ResultadoAnaliseClausula.status_revisao != "descartada",
            db.func.coalesce(
                ResultadoAnaliseClausula.impacto_corrigido,
                ResultadoAnaliseClausula.impacto,
            ) == "alto",
        )
        .scalar()
    )


def resumo(usuario):
    contratos = Contrato.query.filter_by(usuario_id=usuario.id)
    hoje = agora().date()

    total_contratos = contratos.count()
    verificados = contratos.filter_by(status=STATUS_VERIFICADO).count()
    valor_total = (
        db.session.query(db.func.coalesce(db.func.sum(Contrato.valor_total), 0))
        .filter(Contrato.usuario_id == usuario.id)
        .scalar()
    )
    vencendo_em_30_dias = contratos.filter(
        Contrato.data_fim >= hoje,
        Contrato.data_fim <= hoje + timedelta(days=30),
    ).count()
    total_aditivos = (
        Aditivo.query.join(Contrato).filter(Contrato.usuario_id == usuario.id).count()
    )
    contratos_por_tipo = (
        db.session.query(Contrato.tipo_contrato, db.func.count(Contrato.id))
        .filter(Contrato.usuario_id == usuario.id)
        .group_by(Contrato.tipo_contrato)
        .order_by(Contrato.tipo_contrato)
        .all()
    )

    return {
        "clausulas_alto_impacto": _clausulas_alto_impacto(usuario),
        "total_contratos": total_contratos,
        "contratos_pendentes": total_contratos - verificados,
        "contratos_verificados": verificados,
        "valor_total": numero_decimal(valor_total),
        "vencendo_em_30_dias": vencendo_em_30_dias,
        "total_aditivos": total_aditivos,
        "contratos_por_tipo": [
            {"tipo": tipo or "Não informado", "total": total}
            for tipo, total in contratos_por_tipo
        ],
    }
