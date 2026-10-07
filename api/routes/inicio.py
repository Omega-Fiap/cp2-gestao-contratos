from flask import Blueprint, jsonify

bp = Blueprint("inicio", __name__)


@bp.get("/")
def inicio():
    return jsonify({
        "mensagem": "API de contratos funcionando",
        "recursos": [
            "/clientes",
            "/usuarios",
            "/contratos",
            "/clausulas",
            "/aditivos",
            "/historico-status",
            "/swagger/",
        ],
    })
