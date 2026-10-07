from api.extensions import db
from api.utils import agora, iso


class Cliente(db.Model):
    __tablename__ = "cliente"
    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id",
            "documento",
            name="uq_cliente_usuario_documento",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String)
    documento = db.Column(db.String)
    email = db.Column(db.String)
    telefone = db.Column(db.String)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), index=True)
    created_at = db.Column(db.DateTime, default=agora)

    contratos = db.relationship("Contrato", back_populates="cliente")
    usuario = db.relationship("Usuario", back_populates="clientes")

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo,
            "documento": self.documento,
            "email": self.email,
            "telefone": self.telefone,
            "created_at": iso(self.created_at),
        }
