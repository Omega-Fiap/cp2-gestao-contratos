import os

# Rede de segurança: mesmo que alguém chame create_app() sem configuração,
# os testes nunca podem tocar o banco real. Deve rodar antes de importar a API.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "chave-de-teste")

import pytest

from api import create_app
from api.extensions import db


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente_api(app):
    return app.test_client()
