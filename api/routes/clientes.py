from flask import Blueprint, jsonify

from api.http import corpo_json
from api.seguranca import autenticado
from api.services import acesso, clientes

bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@bp.get("")
@autenticado
def listar(usuario):
    return jsonify([cliente.to_dict() for cliente in clientes.listar(usuario)])


@bp.get("/<int:id>")
@autenticado
def buscar(usuario, id):
    return jsonify(acesso.cliente_do_usuario(id, usuario).to_dict())


@bp.post("")
@autenticado
def criar(usuario):
    return jsonify(clientes.criar(usuario, corpo_json()).to_dict()), 201


@bp.put("/<int:id>")
@autenticado
def atualizar(usuario, id):
    return jsonify(clientes.atualizar(usuario, id, corpo_json()).to_dict())


@bp.delete("/<int:id>")
@autenticado
def remover(usuario, id):
    clientes.remover(usuario, id)
    return jsonify({"mensagem": "Cliente removido com sucesso."})
