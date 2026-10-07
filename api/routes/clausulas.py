from flask import Blueprint, jsonify, request

from api.http import corpo_json
from api.seguranca import autenticado
from api.services import clausulas

bp = Blueprint("clausulas", __name__, url_prefix="/clausulas")


@bp.get("")
@autenticado
def listar(usuario):
    itens = clausulas.listar(usuario, request.args.get("contrato_id", type=int))
    return jsonify([item.to_dict() for item in itens])


@bp.get("/<int:id>")
@autenticado
def buscar(usuario, id):
    return jsonify(clausulas.buscar(usuario, id).to_dict())


@bp.post("")
@autenticado
def criar(usuario):
    return jsonify(clausulas.criar(usuario, corpo_json()).to_dict()), 201


@bp.put("/<int:id>")
@autenticado
def atualizar(usuario, id):
    return jsonify(clausulas.atualizar(usuario, id, corpo_json()).to_dict())


@bp.delete("/<int:id>")
@autenticado
def remover(usuario, id):
    clausulas.remover(usuario, id)
    return jsonify({"mensagem": "Cláusula removida com sucesso."})
