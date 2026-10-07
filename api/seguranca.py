from functools import wraps

from flask import current_app, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from api.exceptions import ErroAplicacao
from api.extensions import db
from api.models import Usuario


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def gerar_token(usuario):
    return _serializador().dumps({"id": usuario.id})


def usuario_autenticado():
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None
    try:
        dados = _serializador().loads(
            cabecalho[7:], max_age=current_app.config["TOKEN_VALIDADE_SEGUNDOS"]
        )
    except BadSignature:
        return None
    return db.session.get(Usuario, dados.get("id"))


def autenticado(funcao):
    """Exige login e entrega o usuário como primeiro argumento da rota."""

    @wraps(funcao)
    def interna(*args, **kwargs):
        usuario = usuario_autenticado()
        if not usuario:
            raise ErroAplicacao("Autenticação necessária.", 401)
        return funcao(usuario, *args, **kwargs)

    return interna


def administrador(funcao):
    @wraps(funcao)
    @autenticado
    def interna(usuario, *args, **kwargs):
        if usuario.papel != "admin":
            raise ErroAplicacao("Permissão de administrador necessária.", 403)
        return funcao(usuario, *args, **kwargs)

    return interna
