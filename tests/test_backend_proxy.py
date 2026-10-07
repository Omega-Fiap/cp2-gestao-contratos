from backend import servidor


class RespostaRemota:
    content = b'{"ok": true}'
    status_code = 200
    headers = {"Content-Type": "application/json"}


def test_proxy_encaminha_rota_query_e_token(monkeypatch):
    chamada = {}

    def request_falso(metodo, url, **kwargs):
        chamada.update(metodo=metodo, url=url, **kwargs)
        return RespostaRemota()

    monkeypatch.setattr(servidor, "API_URL", "http://api-teste.invalid")
    monkeypatch.setattr(servidor.requests, "request", request_falso)
    cliente = servidor.app.test_client()

    resposta = cliente.get(
        "/api/contratos?status=pendente",
        headers={"Authorization": "Bearer token-de-teste"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}
    assert chamada["metodo"] == "GET"
    assert chamada["url"] == "http://api-teste.invalid/contratos"
    assert dict(chamada["params"]) == {"status": "pendente"}
    assert chamada["headers"]["Authorization"] == "Bearer token-de-teste"
    assert chamada["timeout"] == 15