from api.extensions import db
from api.utils import agora, iso


class HistoricoStatus(db.Model):
    __tablename__ = "historico_status"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status_anterior = db.Column(db.String)
    status_novo = db.Column(db.String)
    alterado_em = db.Column(db.DateTime, default=agora)
    alterado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"))

    contrato = db.relationship("Contrato", back_populates="historicos")
    usuario = db.relationship("Usuario", back_populates="alteracoes_status")

    def to_dict(self):
        return {
            "id": self.id,
            "contrato_id": self.contrato_id,
            "status_anterior": self.status_anterior,
            "status_novo": self.status_novo,
            "alterado_em": iso(self.alterado_em),
            "alterado_por": self.alterado_por,
            "alterado_por_nome": self.usuario.nome if self.usuario else None,
        }
