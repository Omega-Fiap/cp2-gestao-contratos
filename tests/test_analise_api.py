from datetime import date


from api.extensions import db
from api.integrations import gemini
from api.models import Cliente, Clausula, Contrato


def criar_usuario(cliente_api, nome, email):
    resposta = cliente_api.post(
        "/auth/registrar",
        json={"nome": nome, "email": email, "senha": "senha-segura"},
    )
    assert resposta.status_code == 201
    login = cliente_api.post(
        "/auth/login", json={"email": email, "senha": "senha-segura"}
    )
    return resposta.json, {"Authorization": f"Bearer {login.json['token']}"}


def criar_contrato_com_clausula(usuario_id, cliente_id, numero, descricao):
    contrato = Contrato(
        numero=numero,
        titulo=f"Contrato {numero}",
        cliente_id=cliente_id,
        usuario_id=usuario_id,
        data_inicio=date(2026, 1, 1),
    )
    db.session.add(contrato)
    db.session.flush()
    db.session.add(Clausula(
        contrato_id=contrato.id,
        titulo="Cláusula fictícia",
        descricao=descricao,
        ordem=1,
    ))
    db.session.flush()
    return contrato


def test_analise_exige_sessao_e_isola_contrato(cliente_api):
    usuario_a, headers_a = criar_usuario(cliente_api, "A", "analise-a@example.com")
    usuario_b, _headers_b = criar_usuario(cliente_api, "B", "analise-b@example.com")
    cliente = Cliente(nome="Cliente", usuario_id=usuario_a["id"])
    db.session.add(cliente)
    db.session.flush()
    contrato = criar_contrato_com_clausula(
        usuario_b["id"], cliente.id, "AN-001", "multa de 20%"
    )
    db.session.commit()

    assert cliente_api.post(f"/contratos/{contrato.id}/analisar").status_code == 401
    assert cliente_api.post(
        f"/contratos/{contrato.id}/analisar", headers=headers_a
    ).status_code == 404


def test_analise_persiste_reutiliza_e_reanalisa_ao_mudar_texto(cliente_api, monkeypatch):
    usuario, headers = criar_usuario(cliente_api, "A", "analise-cache@example.com")
    cliente = Cliente(nome="Cliente", usuario_id=usuario["id"])
    db.session.add(cliente)
    db.session.flush()
    contrato = criar_contrato_com_clausula(
        usuario["id"], cliente.id, "AN-002", "Multa de 20% do valor restante."
    )
    db.session.commit()

    chamadas = []

    def analisar_falso(texto):
        chamadas.append(texto)
        return {
            "clausulas": [{
                "tipo": "multa de rescisão",
                "valor_ou_percentual": "20%",
                "impacto": "alto",
                "trecho_original": "Multa de 20%",
            }],
            "modelo": "gemini-fake",
            "versao_prompt": "teste-1",
        }

    monkeypatch.setattr(gemini, "analisar_clausulas", analisar_falso)

    resposta = cliente_api.post(f"/contratos/{contrato.id}/analisar", headers=headers)
    assert resposta.status_code == 201
    assert resposta.json["reutilizada"] is False
    assert resposta.json["clausulas"][0]["trecho_original"] == "Multa de 20%"
    assert chamadas == ["Multa de 20% do valor restante."]

    reutilizada = cliente_api.post(f"/contratos/{contrato.id}/analisar", headers=headers)
    assert reutilizada.status_code == 200
    assert reutilizada.json["reutilizada"] is True
    assert len(chamadas) == 1

    Clausula.query.filter_by(contrato_id=contrato.id).one().descricao = "Multa de 25%."
    db.session.commit()
    atualizada = cliente_api.post(f"/contratos/{contrato.id}/analisar", headers=headers)
    assert atualizada.status_code == 201
    assert atualizada.json["reutilizada"] is False
    assert chamadas[-1] == "Multa de 25%."
    assert len(chamadas) == 2


def test_analise_nao_vaza_dados_do_cliente_e_trata_erros(cliente_api, monkeypatch):
    usuario, headers = criar_usuario(cliente_api, "A", "analise-errors@example.com")
    cliente = Cliente(
        nome="Nome que nao pode ser enviado",
        documento="123.456.789-00",
        usuario_id=usuario["id"],
    )
    db.session.add(cliente)
    db.session.flush()
    contrato = criar_contrato_com_clausula(
        usuario["id"], cliente.id, "AN-003", "A rescisão prevê multa de 20%."
    )
    db.session.commit()

    enviada = []
    monkeypatch.setattr(
        gemini,
        "analisar_clausulas",
        lambda texto: (enviada.append(texto), {
            "clausulas": [], "modelo": "fake", "versao_prompt": "teste"
        })[1],
    )
    resposta = cliente_api.post(f"/contratos/{contrato.id}/analisar", headers=headers)
    assert resposta.status_code == 201
    assert enviada == ["A rescisão prevê multa de 20%."]
    assert "Nome que nao pode ser enviado" not in enviada[0]
    assert "123.456.789-00" not in enviada[0]

    def erro_gemini(_texto):
        raise gemini.ErroAnaliseClausulas("indisponível")

    monkeypatch.setattr(gemini, "analisar_clausulas", erro_gemini)
    Clausula.query.filter_by(contrato_id=contrato.id).one().descricao = "Texto novo sem cache"
    db.session.commit()
    falha = cliente_api.post(f"/contratos/{contrato.id}/analisar", headers=headers)
    assert falha.status_code == 502
    assert falha.json["erro"] == "indisponível"


def test_usuario_pode_confirmar_corrigir_ou_descartar_achado(cliente_api, monkeypatch):
    usuario, headers = criar_usuario(cliente_api, "A", "revisao@example.com")
    cliente = Cliente(nome="Cliente", usuario_id=usuario["id"])
    db.session.add(cliente)
    db.session.flush()
    contrato = criar_contrato_com_clausula(
        usuario["id"], cliente.id, "REV-001", "Multa de 20% do valor restante."
    )
    db.session.commit()

    monkeypatch.setattr(
        gemini,
        "analisar_clausulas",
        lambda _texto: {
            "clausulas": [{
                "tipo": "multa de rescisão",
                "valor_ou_percentual": "20%",
                "impacto": "alto",
                "trecho_original": "Multa de 20%",
            }],
            "modelo": "fake",
            "versao_prompt": "teste",
        },
    )
    resultado = cliente_api.post(f"/contratos/{contrato.id}/analisar", headers=headers)
    achado_id = resultado.json["clausulas"][0]["id"]

    corrigido = cliente_api.put(
        f"/contratos/{contrato.id}/analise/{achado_id}",
        headers=headers,
        json={
            "acao": "corrigir",
            "tipo": "multa de encerramento",
            "valor_ou_percentual": "15%",
            "impacto": "médio",
        },
    )
    assert corrigido.status_code == 200
    assert corrigido.json["status_revisao"] == "corrigida"
    assert corrigido.json["tipo_corrigido"] == "multa de encerramento"
    assert corrigido.json["trecho_original"] == "Multa de 20%"

    confirmada = cliente_api.put(
        f"/contratos/{contrato.id}/analise/{achado_id}",
        headers=headers,
        json={"acao": "confirmar"},
    )
    assert confirmada.json["status_revisao"] == "confirmada"

    descartada = cliente_api.put(
        f"/contratos/{contrato.id}/analise/{achado_id}",
        headers=headers,
        json={"acao": "descartar"},
    )
    assert descartada.json["status_revisao"] == "descartada"
    assert cliente_api.put(
        f"/contratos/{contrato.id}/analise/{achado_id}",
        json={"acao": "confirmar"},
    ).status_code == 401
