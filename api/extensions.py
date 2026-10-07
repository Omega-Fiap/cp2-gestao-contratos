from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from api.exceptions import ErroAplicacao

db = SQLAlchemy()


def salvar():
    """Confirma a transação; violações de unicidade/FK viram erro 409."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ErroAplicacao(
            "Não foi possível salvar. Verifique campos únicos e chaves estrangeiras.",
            409,
        )
