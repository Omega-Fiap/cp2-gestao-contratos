from api.extensions import db
from api.utils import agora, iso


class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    senha_hash = db.Column(db.String, nullable=False)
    papel = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=agora)

    contratos = db.relationship("Contrato", back_populates="usuario")
    clientes = db.relationship("Cliente", back_populates="usuario")
    alteracoes_status = db.relationship("HistoricoStatus", back_populates="usuario")

    def to_dict(self):
        # O hash da senha não é exposto pela API.
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "papel": self.papel,
            "created_at": iso(self.created_at),
        }
