from flask import Blueprint, jsonify

from api.seguranca import autenticado
from api.services import dashboard

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.get("/resumo")
@autenticado
def resumo(usuario):
    return jsonify(dashboard.resumo(usuario))
