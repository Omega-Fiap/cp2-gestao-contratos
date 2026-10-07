from api.extensions import db
from api.utils import iso, numero_decimal


class Aditivo(db.Model):
    __tablename__ = "aditivo"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descricao = db.Column(db.Text, nullable=False)
    novo_valor = db.Column(db.Numeric(12, 2))
    nova_data_fim = db.Column(db.Date)
    data_assinatura = db.Column(db.Date, nullable=False)

    contrato = db.relationship("Contrato", back_populates="aditivos")

    def to_dict(self):
        return {
            "id": self.id,
            "contrato_id": self.contrato_id,
            "descricao": self.descricao,
            "novo_valor": numero_decimal(self.novo_valor),
            "nova_data_fim": iso(self.nova_data_fim),
            "data_assinatura": iso(self.data_assinatura),
        }
