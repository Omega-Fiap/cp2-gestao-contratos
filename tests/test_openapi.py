from api.app import app


def test_especificacao_openapi_e_serviva_e_documenta_rotas_criticas():
    cliente = app.test_client()

    resposta = cliente.get("/static/swagger.json")

    assert resposta.status_code == 200
    especificacao = resposta.get_json()
    assert especificacao["openapi"].startswith("3.")
    assert {"auth", "contratos", "dashboard"} <= {
        tag["name"] for tag in especificacao["tags"]
    }
    assert "/auth/registrar" in especificacao["paths"]
    assert "/contratos" in especificacao["paths"]
    assert "/contratos/{id}/analisar" in especificacao["paths"]
    assert "/contratos/{id}/analise" in especificacao["paths"]
    assert "/contratos/{id}/analise/{clausula_id}" in especificacao["paths"]
    assert "/dashboard/resumo" in especificacao["paths"]
    assert especificacao["paths"]["/contratos"]["get"]["parameters"]