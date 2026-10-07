from flask import Blueprint, jsonify, request

from api.http import corpo_json
from api.seguranca import autenticado
from api.services import analise, contratos
from api.services.acesso import contrato_do_usuario

bp = Blueprint("contratos", __name__, url_prefix="/contratos")


@bp.get("")
@autenticado
def listar(usuario):
    return jsonify(contratos.listar(
        usuario,
        pagina=request.args.get("page", default=1, type=int),
        por_pagina=request.args.get("per_page", default=50, type=int),
        status=request.args.get("status"),
        tipo=request.args.get("tipo_contrato"),
        busca=request.args.get("q"),
    ))


@bp.get("/<int:id>")
@autenticado
def buscar(usuario, id):
    return jsonify(contrato_do_usuario(id, usuario).to_dict())


@bp.post("")
@autenticado
def criar(usuario):
    return jsonify(contratos.criar(usuario, corpo_json()).to_dict()), 201


@bp.put("/<int:id>")
@autenticado
def atualizar(usuario, id):
    return jsonify(contratos.atualizar(usuario, id, corpo_json()).to_dict())


@bp.delete("/<int:id>")
@autenticado
def remover(usuario, id):
    contratos.remover(usuario, id)
    return jsonify({"mensagem": "Contrato removido com sucesso."})


@bp.post("/<int:id>/verificar")
@autenticado
def verificar(usuario, id):
    return jsonify(contratos.verificar(usuario, id).to_dict())


@bp.post("/<int:id>/analisar")
@autenticado
def analisar(usuario, id):
    resposta, status = analise.analisar(usuario, id)
    return jsonify(resposta), status


@bp.get("/<int:id>/analise")
@autenticado
def buscar_analise(usuario, id):
    return jsonify(analise.buscar(usuario, id))


@bp.put("/<int:id>/analise/<int:clausula_id>")
@autenticado
def revisar_analise(usuario, id, clausula_id):
    resultado = analise.revisar(usuario, id, clausula_id, corpo_json())
    return jsonify(resultado.to_dict())
