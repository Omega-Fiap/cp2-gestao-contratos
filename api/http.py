from flask import request

from api.exceptions import ErroAplicacao


def corpo_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ErroAplicacao("Envie um JSON válido.")
    return dados
