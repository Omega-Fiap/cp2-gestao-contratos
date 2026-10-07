from flask import Blueprint, jsonify

from api.exceptions import ErroAplicacao
from api.http import corpo_json
from api.seguranca import gerar_token, usuario_autenticado
from api.services import contas

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/login")
def login():
    usuario = contas.autenticar(corpo_json())
    return jsonify({"token": gerar_token(usuario), "usuario": usuario.to_dict()})


@bp.post("/registrar")
def registrar():
    return jsonify(contas.registrar(corpo_json()).to_dict()), 201


@bp.get("/me")
def perfil():
    usuario = usuario_autenticado()
    if not usuario:
        raise ErroAplicacao("Sessão inválida ou expirada.", 401)
    return jsonify(usuario.to_dict())
