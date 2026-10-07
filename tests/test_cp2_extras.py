from datetime import date

import pytest

from api.extensions import db
from api.models import (
    AnaliseContrato,
    Cliente,
    Contrato,
    ResultadoAnaliseClausula,
)


def autenticar(cliente_api, email):
    usuario = cliente_api.post(
        "/auth/registrar",
        json={"nome": "Teste", "email": email, "senha": "senha-segura"},
    ).json
    token = cliente_api.post(
        "/auth/login", json={"email": email, "senha": "senha-segura"}
    ).json["token"]
    return usuario, {"Authorization": f"Bearer {token}"}


def criar_contrato(usuario_id):
    cliente = Cliente(nome="Cliente", usuario_id=usuario_id)
    db.session.add(cliente)
    db.session.flush()
    contrato = Contrato(
        numero="X-1",
        titulo="Contrato",
        cliente_id=cliente.id,
        usuario_id=usuario_id,
        data_inicio=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
    )
    db.session.add(contrato)
    db.session.commit()
    return contrato


def test_testes_usam_sqlite_em_memoria_e_nunca_o_banco_real(cliente_api):
    assert db.engine.url.drivername == "sqlite"
    assert db.engine.url.database in (None, "", ":memory:")


def test_put_contrato_rejeita_valor_negativo_e_termino_antes_do_inicio(cliente_api):
    usuario, headers = autenticar(cliente_api, "put@example.com")
    contrato = criar_contrato(usuario["id"])
    url = f"/contratos/{contrato.id}"

    assert cliente_api.put(url, json={"valor_total": -1}, headers=headers).status_code == 400
    assert cliente_api.put(
        url, json={"data_fim": "2025-01-01"}, headers=headers
    ).status_code == 400
    ok = cliente_api.put(url, json={"valor_total": 10, "data_fim": "2027-01-01"}, headers=headers)
    assert ok.status_code == 200
    assert ok.json["valor_total"] == 10


def test_dashboard_conta_clausulas_de_alto_impacto_com_revisao(cliente_api):
    usuario, headers = autenticar(cliente_api, "impacto@example.com")
    contrato = criar_contrato(usuario["id"])
    analise = AnaliseContrato(
        contrato_id=contrato.id, texto_hash="h", modelo="m", versao_prompt="v"
    )
    db.session.add(analise)
    db.session.flush()
    for impacto, extra in [
        ("alto", {}),
        ("alto", {"status_revisao": "descartada"}),
        ("baixo", {"impacto_corrigido": "alto", "status_revisao": "corrigida"}),
        ("médio", {}),
    ]:
        db.session.add(ResultadoAnaliseClausula(
            analise_id=analise.id, tipo="multa", impacto=impacto,
            trecho_original="t", **extra,
        ))
    db.session.commit()

    resumo = cliente_api.get("/dashboard/resumo", headers=headers).json
    assert resumo["clausulas_alto_impacto"] == 2


def test_swagger_documenta_todos_os_recursos(cliente_api):
    paths = cliente_api.get("/static/swagger.json").json["paths"]
    for rota in ["/aditivos", "/aditivos/{id}", "/historico-status", "/usuarios",
                 "/usuarios/{id}", "/clientes/{id}", "/clausulas/{id}"]:
        assert rota in paths


def _contrato_para_editar(cliente_api):
    _, cabecalho = autenticar(cliente_api, "edicao@example.com")
    cliente = cliente_api.post("/clientes", json={"nome": "Cliente"}, headers=cabecalho).json
    contrato = cliente_api.post(
        "/contratos",
        json={
            "numero": "CT-E1",
            "titulo": "Original",
            "cliente_id": cliente["id"],
            "data_inicio": "2026-01-01",
            "data_fim": "2026-12-31",
            "valor_total": 1000,
        },
        headers=cabecalho,
    ).json
    return cabecalho, contrato


def test_put_contrato_atualiza_campos_e_converte_valor(cliente_api):
    cabecalho, contrato = _contrato_para_editar(cliente_api)

    resposta = cliente_api.put(
        f"/contratos/{contrato['id']}",
        json={"titulo": "Novo título", "valor_total": "2500.50", "data_fim": None},
        headers=cabecalho,
    )

    assert resposta.status_code == 200
    assert resposta.json["titulo"] == "Novo título"
    assert resposta.json["valor_total"] == 2500.5
    assert resposta.json["data_fim"] is None


@pytest.mark.parametrize(
    "corpo, mensagem",
    [
        ({"valor_total": -1}, "O valor total não pode ser negativo."),
        ({"valor_total": "abc"}, "Valor total inválido."),
        ({"data_fim": "2025-01-01"}, "A data de término não pode ser anterior ao início."),
        ({"data_inicio": "01/02/2026"}, "Datas devem usar o formato YYYY-MM-DD."),
    ],
)
def test_put_contrato_rejeita_dados_invalidos_e_nao_altera(cliente_api, corpo, mensagem):
    cabecalho, contrato = _contrato_para_editar(cliente_api)

    resposta = cliente_api.put(
        f"/contratos/{contrato['id']}", json=corpo, headers=cabecalho
    )

    assert resposta.status_code == 400
    assert resposta.json["erro"] == mensagem
    atual = cliente_api.get(f"/contratos/{contrato['id']}", headers=cabecalho).json
    assert atual["valor_total"] == 1000
    assert atual["data_fim"] == "2026-12-31"
