from api.routes import (
    aditivos,
    auth,
    clausulas,
    clientes,
    contratos,
    dashboard,
    formulario,
    historico_status,
    inicio,
    usuarios,
)

BLUEPRINTS = [
    inicio, auth, clientes, usuarios, contratos, clausulas,
    aditivos, historico_status, dashboard, formulario,
]


def registrar_rotas(app):
    for modulo in BLUEPRINTS:
        app.register_blueprint(modulo.bp)
