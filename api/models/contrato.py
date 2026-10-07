from api.extensions import db
from api.models.historico_status import HistoricoStatus
from api.utils import agora, iso, numero_decimal

# Status usados pelo fluxo de verificação.
STATUS_PENDENTE = "pendente"
STATUS_VERIFICADO = "verificado"


class Contrato(db.Model):
    __tablename__ = "contrato"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String, nullable=False, unique=True)
    titulo = db.Column(db.String, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    tipo_contrato = db.Column(db.String)
    valor_total = db.Column(db.Numeric(12, 2))
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    status = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=agora)
    updated_at = db.Column(
        db.DateTime,
        default=agora,
        onupdate=agora,
    )

    cliente = db.relationship("Cliente", back_populates="contratos")
    usuario = db.relationship("Usuario", back_populates="contratos")
    # cascade: ao excluir um contrato, remove cláusulas, aditivos e histórico dele.
    clausulas = db.relationship(
        "Clausula", back_populates="contrato", cascade="all, delete-orphan"
    )
    aditivos = db.relationship(
        "Aditivo", back_populates="contrato", cascade="all, delete-orphan"
    )
    historicos = db.relationship(
        "HistoricoStatus", back_populates="contrato", cascade="all, delete-orphan"
    )
    analise = db.relationship(
        "AnaliseContrato",
        back_populates="contrato",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def dados_verificacao(self):
        """Retorna (nome de quem verificou, data/hora) a partir do histórico."""
        if self.status != STATUS_VERIFICADO:
            return None, None

        registro = (
            HistoricoStatus.query
            .filter_by(contrato_id=self.id, status_novo=STATUS_VERIFICADO)
            .order_by(HistoricoStatus.alterado_em.desc(), HistoricoStatus.id.desc())
            .first()
        )
        if registro is None:
            return None, None

        nome = registro.usuario.nome if registro.usuario else None
        return nome, iso(registro.alterado_em)

    def to_dict(self):
        verificado_por, verificado_em = self.dados_verificacao()
        return {
            "id": self.id,
            "numero": self.numero,
            "titulo": self.titulo,
            "cliente_id": self.cliente_id,
            "tipo_contrato": self.tipo_contrato,
            "valor_total": numero_decimal(self.valor_total),
            "data_inicio": iso(self.data_inicio),
            "data_fim": iso(self.data_fim),
            "status": self.status,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "verificado_por": verificado_por,
            "verificado_em": verificado_em,
        }
