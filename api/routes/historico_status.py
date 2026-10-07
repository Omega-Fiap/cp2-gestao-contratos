from flask import Blueprint, jsonify, request

from api.http import corpo_json
from api.seguranca import autenticado
from api.services import historico_status

bp = Blueprint("historico_status", __name__, url_prefix="/historico-status")


@bp.get("")
@autenticado
def listar(usuario):
    itens = historico_status.listar(usuario, request.args.get("contrato_id", type=int))
    return jsonify([item.to_dict() for item in itens])


@bp.get("/<int:id>")
@autenticado
def buscar(usuario, id):
    return jsonify(historico_status.buscar(usuario, id).to_dict())


@bp.post("")
@autenticado
def criar(usuario):
    return jsonify(historico_status.criar(usuario, corpo_json()).to_dict()), 201


@bp.put("/<int:id>")
@autenticado
def atualizar(usuario, id):
    return jsonify(historico_status.atualizar(usuario, id, corpo_json()).to_dict())


@bp.delete("/<int:id>")
@autenticado
def remover(usuario, id):
    historico_status.remover(usuario, id)
    return jsonify({"mensagem": "Histórico de status removido com sucesso."})
