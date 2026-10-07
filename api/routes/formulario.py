from flask import Blueprint, jsonify

from api.http import corpo_json
from api.seguranca import autenticado
from api.services import formulario

bp = Blueprint("formulario", __name__)


@bp.post("/formulario")
@autenticado
def receber(usuario):
    contrato = formulario.receber(usuario, corpo_json())
    return jsonify({
        "mensagem": "Formulário recebido com sucesso.",
        "contrato": contrato.to_dict(),
    }), 201
