from api.extensions import db


class Clausula(db.Model):
    __tablename__ = "clausula"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo = db.Column(db.String)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer)

    contrato = db.relationship("Contrato", back_populates="clausulas")

    def to_dict(self):
        return {
            "id": self.id,
            "contrato_id": self.contrato_id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "ordem": self.ordem,
        }
