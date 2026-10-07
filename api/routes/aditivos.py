from flask import Blueprint, jsonify, request

from api.http import corpo_json
from api.seguranca import autenticado
from api.services import aditivos

bp = Blueprint("aditivos", __name__, url_prefix="/aditivos")


@bp.get("")
@autenticado
def listar(usuario):
    itens = aditivos.listar(usuario, request.args.get("contrato_id", type=int))
    return jsonify([item.to_dict() for item in itens])


@bp.get("/<int:id>")
@autenticado
def buscar(usuario, id):
    return jsonify(aditivos.buscar(usuario, id).to_dict())


@bp.post("")
@autenticado
def criar(usuario):
    return jsonify(aditivos.criar(usuario, corpo_json()).to_dict()), 201


@bp.put("/<int:id>")
@autenticado
def atualizar(usuario, id):
    return jsonify(aditivos.atualizar(usuario, id, corpo_json()).to_dict())


@bp.delete("/<int:id>")
@autenticado
def remover(usuario, id):
    aditivos.remover(usuario, id)
    return jsonify({"mensagem": "Aditivo removido com sucesso."})
