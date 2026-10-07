
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint

from api.config import Config
from api.errors import registrar_tratadores_de_erro
from api.extensions import db


def create_app(config=None):
    """Factory da API. `config` (dict) sobrescreve os valores de api.config.Config."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    db.init_app(app)

    @app.after_request
    def liberar_cors(resposta):
        # Permite que o front-end (outra porta/origem) consuma a API.
        resposta.headers["Access-Control-Allow-Origin"] = app.config["CORS_ORIGIN"]
        resposta.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resposta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return resposta

    app.register_blueprint(
        get_swaggerui_blueprint(
            "/swagger",
            "/static/swagger.json",
            config={"app_name": "API Flask - Gestão de Contratos"},
        ),
        url_prefix="/swagger",
    )

    from api.routes import registrar_rotas

    registrar_rotas(app)
    registrar_tratadores_de_erro(app)
    return app
