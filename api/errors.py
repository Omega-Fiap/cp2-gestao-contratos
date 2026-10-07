from flask import jsonify

from api.exceptions import ErroAplicacao
from api.extensions import db


def erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def registrar_tratadores_de_erro(app):
    @app.errorhandler(ErroAplicacao)
    def erro_da_aplicacao(exc):
        db.session.rollback()
        return erro(exc.mensagem, exc.status)

    @app.errorhandler(404)
    def rota_nao_encontrada(_):
        return erro("Rota não encontrada.", 404)

    @app.errorhandler(500)
    def erro_interno(_):
        db.session.rollback()
        return erro("Erro interno do servidor.", 500)
