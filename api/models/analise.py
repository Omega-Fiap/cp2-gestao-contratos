from api.extensions import db
from api.utils import agora, iso


class AnaliseContrato(db.Model):
    __tablename__ = "analise_contrato"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    texto_hash = db.Column(db.String(64), nullable=False)
    modelo = db.Column(db.String, nullable=False)
    versao_prompt = db.Column(db.String, nullable=False)
    analisado_em = db.Column(db.DateTime, default=agora, nullable=False)

    contrato = db.relationship("Contrato", back_populates="analise")
    clausulas = db.relationship(
        "ResultadoAnaliseClausula",
        back_populates="analise",
        cascade="all, delete-orphan",
    )


class ResultadoAnaliseClausula(db.Model):
    __tablename__ = "resultado_analise_clausula"

    id = db.Column(db.Integer, primary_key=True)
    analise_id = db.Column(
        db.Integer,
        db.ForeignKey("analise_contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String, nullable=False)
    valor_ou_percentual = db.Column(db.String, nullable=False, default="")
    impacto = db.Column(db.String, nullable=False)
    trecho_original = db.Column(db.Text, nullable=False)
    status_revisao = db.Column(db.String, nullable=False, default="pendente")
    tipo_corrigido = db.Column(db.String)
    valor_corrigido = db.Column(db.String)
    impacto_corrigido = db.Column(db.String)
    revisado_em = db.Column(db.DateTime)

    analise = db.relationship("AnaliseContrato", back_populates="clausulas")

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "valor_ou_percentual": self.valor_ou_percentual,
            "impacto": self.impacto,
            "trecho_original": self.trecho_original,
            "status_revisao": self.status_revisao,
            "tipo_corrigido": self.tipo_corrigido,
            "valor_corrigido": self.valor_corrigido,
            "impacto_corrigido": self.impacto_corrigido,
            "revisado_em": iso(self.revisado_em),
        }
