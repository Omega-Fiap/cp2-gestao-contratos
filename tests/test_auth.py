from datetime import date, timedelta
from decimal import Decimal

from api.extensions import db
from api.utils import agora
from api.models import (
    Aditivo,
    Cliente,
    Clausula,
    Contrato,
    HistoricoStatus,
    Usuario,
)


def test_autocadastro_ignora_papel_enviado_e_cria_usuario(cliente_api):
    resposta = cliente_api.post(
        "/auth/registrar",
        json={
            "nome": "Pessoa de teste",
            "email": "teste@example.com",
            "senha": "senha-segura",
            "papel": "admin",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json["papel"] == "usuario"
    assert Usuario.query.filter_by(email="teste@example.com").one().papel == "usuario"


def test_crud_de_usuarios_nao_permite_autopromocao(cliente_api):
    usuario, headers = criar_usuario_autenticado(
        cliente_api, "Conta comum", "conta-comum@example.com"
    )

    assert cliente_api.get("/usuarios").status_code == 401
    assert cliente_api.post(
        "/usuarios",
        json={"nome": "Admin falso", "email": "falso@example.com", "papel": "admin"},
    ).status_code == 405
    assert cliente_api.get("/usuarios", headers=headers).status_code == 403
    assert cliente_api.get(
        f"/usuarios/{usuario['id']}", headers=headers
    ).status_code == 200
    assert cliente_api.get("/usuarios/999", headers=headers).status_code == 404
    assert cliente_api.put(
        f"/usuarios/{usuario['id']}",
        headers=headers,
        json={"papel": "admin"},
    ).status_code == 403


def criar_usuario_autenticado(cliente_api, nome, email):
    resposta = cliente_api.post(
        "/auth/registrar",
        json={"nome": nome, "email": email, "senha": "senha-segura"},
    )
    assert resposta.status_code == 201
    login = cliente_api.post(
        "/auth/login",
        json={"email": email, "senha": "senha-segura"},
    )
    return resposta.json, {"Authorization": f"Bearer {login.json['token']}"}


def criar_contrato(usuario_id, cliente_id, numero):
    contrato = Contrato(
        numero=numero,
        titulo=f"Contrato {numero}",
        cliente_id=cliente_id,
        usuario_id=usuario_id,
        data_inicio=date(2026, 1, 1),
    )
    db.session.add(contrato)
    db.session.flush()
    return contrato


def test_contratos_exigem_token_e_isolam_operacoes_por_usuario(cliente_api):
    sem_token = cliente_api.get("/contratos")
    assert sem_token.status_code == 401

    usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "a@example.com"
    )
    usuario_b, headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "b@example.com"
    )
    cliente = Cliente(nome="Cliente de teste", usuario_id=usuario_a["id"])
    db.session.add(cliente)
    db.session.flush()
    contrato_a = criar_contrato(usuario_a["id"], cliente.id, "A-001")
    contrato_b = criar_contrato(usuario_b["id"], cliente.id, "B-001")
    db.session.commit()

    lista_a = cliente_api.get("/contratos", headers=headers_a)
    assert [item["numero"] for item in lista_a.json["items"]] == ["A-001"]
    assert lista_a.json["pagination"]["total"] == 1
    assert cliente_api.get(f"/contratos/{contrato_b.id}", headers=headers_a).status_code == 404
    assert cliente_api.put(
        f"/contratos/{contrato_b.id}",
        headers=headers_a,
        json={"titulo": "Acesso indevido"},
    ).status_code == 404
    assert cliente_api.delete(
        f"/contratos/{contrato_b.id}", headers=headers_a
    ).status_code == 404

    criado = cliente_api.post(
        "/contratos",
        headers=headers_a,
        json={
            "numero": "A-002",
            "titulo": "Contrato novo",
            "cliente_id": cliente.id,
            "usuario_id": usuario_b["id"],
            "data_inicio": "2026-01-01",
        },
    )
    assert criado.status_code == 201
    contrato_criado = Contrato.query.filter_by(numero="A-002").one()
    assert contrato_criado.usuario_id == usuario_a["id"]


def test_clausulas_exigem_token_e_verificam_dono_do_contrato(cliente_api):
    usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "clausula-a@example.com"
    )
    usuario_b, headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "clausula-b@example.com"
    )
    cliente = Cliente(nome="Cliente de cláusula")
    db.session.add(cliente)
    db.session.flush()
    contrato_a = criar_contrato(usuario_a["id"], cliente.id, "CA-001")
    contrato_b = criar_contrato(usuario_b["id"], cliente.id, "CB-001")
    clausula_b = Clausula(
        contrato_id=contrato_b.id,
        titulo="Cláusula privada",
        descricao="Conteúdo do usuário B",
    )
    db.session.add(clausula_b)
    db.session.commit()

    assert cliente_api.get("/clausulas").status_code == 401
    assert cliente_api.get("/clausulas", headers=headers_a).json == []
    assert cliente_api.get(
        f"/clausulas/{clausula_b.id}", headers=headers_a
    ).status_code == 404
    assert cliente_api.put(
        f"/clausulas/{clausula_b.id}",
        headers=headers_a,
        json={"titulo": "Alteração indevida"},
    ).status_code == 404
    assert cliente_api.delete(
        f"/clausulas/{clausula_b.id}", headers=headers_a
    ).status_code == 404

    criada = cliente_api.post(
        "/clausulas",
        headers=headers_a,
        json={"contrato_id": contrato_b.id, "titulo": "Cláusula alheia"},
    )
    assert criada.status_code == 404

    mover = cliente_api.post(
        "/clausulas",
        headers=headers_b,
        json={"contrato_id": contrato_b.id, "titulo": "Cláusula B"},
    )
    assert mover.status_code == 201
    assert cliente_api.put(
        f"/clausulas/{mover.json['id']}",
        headers=headers_b,
        json={"contrato_id": contrato_a.id},
    ).status_code == 404


def test_descricao_de_clausula_tem_limite_e_deve_ser_texto(cliente_api):
    usuario, headers = criar_usuario_autenticado(
        cliente_api, "Usuário limite", "limite@example.com"
    )
    cliente = Cliente(nome="Cliente limite", usuario_id=usuario["id"])
    db.session.add(cliente)
    db.session.flush()
    contrato = criar_contrato(usuario["id"], cliente.id, "LIM-001")
    db.session.commit()

    url = "/clausulas"
    base = {"contrato_id": contrato.id, "titulo": "Cláusula"}
    grande = cliente_api.post(
        url,
        headers=headers,
        json={**base, "descricao": "x" * 30_001},
    )
    assert grande.status_code == 400
    tipo_invalido = cliente_api.post(
        url,
        headers=headers,
        json={**base, "descricao": {"texto": "não é string"}},
    )
    assert tipo_invalido.status_code == 400

    formulario = cliente_api.post(
        "/formulario",
        headers=headers,
        json={
            "cliente": {"nome": "Cliente"},
            "contrato": {"titulo": "Outro", "data_inicio": "2026-01-01"},
            "clausulas": [{"descricao": "x" * 30_001}],
        },
    )
    assert formulario.status_code == 400


def test_aditivos_historico_e_verificacao_respeitam_dono_do_contrato(cliente_api):
    usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "relacionados-a@example.com"
    )
    usuario_b, headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "relacionados-b@example.com"
    )
    cliente = Cliente(nome="Cliente dos relacionados")
    db.session.add(cliente)
    db.session.flush()
    contrato_a = criar_contrato(usuario_a["id"], cliente.id, "RA-001")
    contrato_b = criar_contrato(usuario_b["id"], cliente.id, "RB-001")
    aditivo_b = Aditivo(
        contrato_id=contrato_b.id,
        descricao="Aditivo privado",
        data_assinatura=date(2026, 1, 2),
    )
    historico_b = HistoricoStatus(
        contrato_id=contrato_b.id,
        status_anterior="pendente",
        status_novo="verificado",
    )
    db.session.add_all([aditivo_b, historico_b])
    db.session.commit()

    assert cliente_api.get("/aditivos").status_code == 401
    assert cliente_api.get("/historico-status").status_code == 401
    assert cliente_api.get("/aditivos", headers=headers_a).json == []
    assert cliente_api.get("/historico-status", headers=headers_a).json == []
    assert cliente_api.get(
        f"/aditivos/{aditivo_b.id}", headers=headers_a
    ).status_code == 404
    assert cliente_api.delete(
        f"/aditivos/{aditivo_b.id}", headers=headers_a
    ).status_code == 404
    assert cliente_api.get(
        f"/historico-status/{historico_b.id}", headers=headers_a
    ).status_code == 404
    assert cliente_api.put(
        f"/historico-status/{historico_b.id}",
        headers=headers_a,
        json={"status_novo": "alterado indevidamente"},
    ).status_code == 404
    assert cliente_api.post(
        f"/contratos/{contrato_b.id}/verificar", headers=headers_a
    ).status_code == 404

    criado = cliente_api.post(
        "/aditivos",
        headers=headers_a,
        json={
            "contrato_id": contrato_b.id,
            "descricao": "Aditivo alheio",
            "data_assinatura": "2026-01-03",
        },
    )
    assert criado.status_code == 404

    historico = cliente_api.post(
        "/historico-status",
        headers=headers_a,
        json={
            "contrato_id": contrato_a.id,
            "status_novo": "pendente",
            "alterado_por": usuario_b["id"],
        },
    )
    assert historico.status_code == 201
    assert historico.json["alterado_por"] == usuario_a["id"]


def test_resumo_dashboard_exige_token_e_usa_apenas_dados_do_usuario(cliente_api):
    usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "resumo-a@example.com"
    )
    usuario_b, _headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "resumo-b@example.com"
    )
    cliente = Cliente(nome="Cliente do resumo")
    db.session.add(cliente)
    db.session.flush()
    contrato_a = criar_contrato(usuario_a["id"], cliente.id, "DA-001")
    contrato_a.valor_total = Decimal("1250.50")
    contrato_a.tipo_contrato = "Serviço"
    contrato_a.data_fim = agora().date() + timedelta(days=10)
    contrato_b = criar_contrato(usuario_b["id"], cliente.id, "DB-001")
    contrato_b.valor_total = Decimal("9000.00")
    contrato_b.tipo_contrato = "Locação"
    db.session.add(Aditivo(
        contrato_id=contrato_a.id,
        descricao="Aditivo de teste",
        data_assinatura=date(2026, 1, 4),
    ))
    db.session.commit()

    assert cliente_api.get("/dashboard/resumo").status_code == 401
    resposta = cliente_api.get("/dashboard/resumo", headers=headers_a)

    assert resposta.status_code == 200
    assert resposta.json == {
        "clausulas_alto_impacto": 0,
        "total_contratos": 1,
        "contratos_pendentes": 1,
        "contratos_verificados": 0,
        "valor_total": 1250.5,
        "vencendo_em_30_dias": 1,
        "total_aditivos": 1,
        "contratos_por_tipo": [{"tipo": "Serviço", "total": 1}],
    }


def test_formulario_exige_sessao_e_cria_registros_na_carteira(cliente_api):
    usuario, headers = criar_usuario_autenticado(
        cliente_api, "Usuário formulário", "formulario@example.com"
    )
    corpo = {
        "cliente": {
            "nome": "Cliente carteira A",
            "documento": "DOC-PRIVADO-1",
            "email": "cliente-a@example.com",
        },
        "contrato": {
            "titulo": "Contrato da carteira A",
            "tipo_contrato": "Serviço",
            "data_inicio": "2026-01-01",
        },
        "clausulas": [],
    }

    assert cliente_api.post("/formulario", json=corpo).status_code == 401
    resposta = cliente_api.post("/formulario", json=corpo, headers=headers)

    assert resposta.status_code == 201
    contrato = Contrato.query.filter_by(numero=resposta.json["contrato"]["numero"]).one()
    cliente = db.session.get(Cliente, contrato.cliente_id)
    assert contrato.usuario_id == usuario["id"]
    assert cliente.usuario_id == usuario["id"]


def test_formulario_nao_reutiliza_cliente_de_outra_carteira(cliente_api):
    usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "form-a@example.com"
    )
    usuario_b, headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "form-b@example.com"
    )
    corpo = {
        "cliente": {"nome": "Cliente privado A", "documento": "DOC-REPETIDO"},
        "contrato": {"titulo": "Contrato A", "data_inicio": "2026-01-01"},
        "clausulas": [],
    }
    resposta_a = cliente_api.post("/formulario", json=corpo, headers=headers_a)
    corpo["cliente"]["nome"] = "Cliente privado B"
    corpo["contrato"]["titulo"] = "Contrato B"
    resposta_b = cliente_api.post("/formulario", json=corpo, headers=headers_b)

    assert resposta_a.status_code == 201
    assert resposta_b.status_code == 201
    contrato_a = Contrato.query.filter_by(numero=resposta_a.json["contrato"]["numero"]).one()
    contrato_b = Contrato.query.filter_by(numero=resposta_b.json["contrato"]["numero"]).one()
    assert contrato_a.usuario_id == usuario_a["id"]
    assert contrato_b.usuario_id == usuario_b["id"]
    assert contrato_a.cliente_id != contrato_b.cliente_id


def test_listagem_contratos_tem_paginacao_filtros_e_limite(cliente_api):
    usuario, headers = criar_usuario_autenticado(
        cliente_api, "Usuário filtros", "filtros@example.com"
    )
    cliente = Cliente(nome="Cliente Filtrado", usuario_id=usuario["id"])
    db.session.add(cliente)
    db.session.flush()
    primeiro = criar_contrato(usuario["id"], cliente.id, "PG-001")
    primeiro.tipo_contrato = "Serviço"
    primeiro.status = "pendente"
    segundo = criar_contrato(usuario["id"], cliente.id, "PG-002")
    segundo.tipo_contrato = "Locação"
    segundo.status = "verificado"
    terceiro = criar_contrato(usuario["id"], cliente.id, "PG-003")
    terceiro.tipo_contrato = "Serviço"
    terceiro.status = "pendente"
    db.session.commit()

    pagina = cliente_api.get("/contratos?page=2&per_page=1", headers=headers)
    assert pagina.status_code == 200
    assert [item["numero"] for item in pagina.json["items"]] == ["PG-002"]
    assert pagina.json["pagination"] == {
        "page": 2,
        "per_page": 1,
        "total": 3,
        "pages": 3,
    }

    filtrado = cliente_api.get(
        "/contratos?status=pendente&tipo_contrato=Servi%C3%A7o&q=PG-003",
        headers=headers,
    )
    assert [item["numero"] for item in filtrado.json["items"]] == ["PG-003"]
    assert filtrado.json["pagination"]["total"] == 1

    limite = cliente_api.get("/contratos?per_page=500", headers=headers)
    assert limite.json["pagination"]["per_page"] == 100
    assert cliente_api.get("/contratos?page=0", headers=headers).status_code == 400


def test_clientes_sao_privados_e_contrato_nao_aceita_cliente_alheio(cliente_api):
    usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "cliente-privado-a@example.com"
    )
    usuario_b, headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "cliente-privado-b@example.com"
    )

    criado_b = cliente_api.post(
        "/clientes",
        headers=headers_b,
        json={"nome": "Cliente privado B", "documento": "DOC-B"},
    )
    assert criado_b.status_code == 201
    assert db.session.get(Cliente, criado_b.json["id"]).usuario_id == usuario_b["id"]
    assert cliente_api.get("/clientes").status_code == 401
    assert cliente_api.get("/clientes", headers=headers_a).json == []
    assert cliente_api.get(
        f"/clientes/{criado_b.json['id']}", headers=headers_a
    ).status_code == 404
    assert cliente_api.put(
        f"/clientes/{criado_b.json['id']}",
        headers=headers_a,
        json={"nome": "Alteração indevida"},
    ).status_code == 404
    assert cliente_api.delete(
        f"/clientes/{criado_b.json['id']}", headers=headers_a
    ).status_code == 404

    contrato = cliente_api.post(
        "/contratos",
        headers=headers_a,
        json={
            "numero": "CLIENTE-ALHEIO",
            "titulo": "Não pode associar",
            "cliente_id": criado_b.json["id"],
            "data_inicio": "2026-01-01",
        },
    )
    assert contrato.status_code == 404


def test_documento_de_cliente_e_unico_dentro_da_carteira(cliente_api):
    _usuario_a, headers_a = criar_usuario_autenticado(
        cliente_api, "Usuário A", "documento-a@example.com"
    )
    _usuario_b, headers_b = criar_usuario_autenticado(
        cliente_api, "Usuário B", "documento-b@example.com"
    )
    dados = {"nome": "Cliente com documento", "documento": "DOC-COMUM"}

    assert cliente_api.post("/clientes", headers=headers_a, json=dados).status_code == 201
    assert cliente_api.post("/clientes", headers=headers_b, json=dados).status_code == 201
    duplicado = cliente_api.post("/clientes", headers=headers_a, json=dados)
    assert duplicado.status_code == 409