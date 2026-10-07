from flask import Blueprint, jsonify

from api.exceptions import ErroAplicacao
from api.http import corpo_json
from api.seguranca import administrador, autenticado
from api.services import contas

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.get("")
@administrador
def listar(usuario):
    return jsonify([item.to_dict() for item in contas.listar()])


@bp.get("/<int:id>")
@autenticado
def buscar(usuario, id):
    return jsonify(contas.buscar(usuario, id).to_dict())


@bp.post("")
def criar():
    raise ErroAplicacao("Use o endpoint /auth/registrar para criar uma conta.", 405)


@bp.put("/<int:id>")
@administrador
def atualizar(usuario, id):
    return jsonify(contas.atualizar(id, corpo_json()).to_dict())


@bp.delete("/<int:id>")
@administrador
def remover(usuario, id):
    contas.remover(id)
    return jsonify({"mensagem": "Usuário removido com sucesso."})
