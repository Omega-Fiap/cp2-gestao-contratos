from decimal import Decimal, InvalidOperation

from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import STATUS_VERIFICADO, Cliente, Contrato, HistoricoStatus
from api.services.acesso import cliente_do_usuario, contrato_do_usuario
from api.utils import agora, data_ou_erro, texto

POR_PAGINA_MAXIMO = 100
CAMPOS_SIMPLES = ["numero", "titulo", "cliente_id", "tipo_contrato", "valor_total", "status"]


def validar_valor(valor):
    """Converte para Decimal; vazio vira None. Rejeita inválido e negativo."""
    if valor in (None, ""):
        return None
    try:
        decimal = Decimal(str(valor))
    except InvalidOperation:
        raise ErroAplicacao("Valor total inválido.")
    if decimal < 0:
        raise ErroAplicacao("O valor total não pode ser negativo.")
    return decimal


def validar_periodo(data_inicio, data_fim):
    if data_fim and data_inicio and data_fim < data_inicio:
        raise ErroAplicacao("A data de término não pode ser anterior ao início.")


def listar(usuario, pagina, por_pagina, status=None, tipo=None, busca=None):
    if pagina < 1 or por_pagina < 1:
        raise ErroAplicacao("page e per_page devem ser inteiros positivos.")
    por_pagina = min(por_pagina, POR_PAGINA_MAXIMO)

    consulta = Contrato.query.filter_by(usuario_id=usuario.id)
    if status := texto(status):
        consulta = consulta.filter(Contrato.status == status)
    if tipo := texto(tipo):
        consulta = consulta.filter(Contrato.tipo_contrato == tipo)
    if busca := texto(busca):
        padrao = f"%{busca}%"
        consulta = consulta.join(Cliente).filter(
            db.or_(
                Contrato.numero.ilike(padrao),
                Contrato.titulo.ilike(padrao),
                Cliente.nome.ilike(padrao),
            )
        )

    total = consulta.count()
    contratos = (
        consulta.order_by(Contrato.id)
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    return {
        "items": [contrato.to_dict() for contrato in contratos],
        "pagination": {
            "page": pagina,
            "per_page": por_pagina,
            "total": total,
            "pages": (total + por_pagina - 1) // por_pagina,
        },
    }


def criar(usuario, dados):
    obrigatorios = ["numero", "titulo", "cliente_id", "data_inicio"]
    faltando = [campo for campo in obrigatorios if dados.get(campo) in (None, "")]
    if faltando:
        raise ErroAplicacao(f"Campos obrigatórios: {', '.join(faltando)}.")
    cliente_do_usuario(dados["cliente_id"], usuario)

    contrato = Contrato(
        numero=dados["numero"],
        titulo=dados["titulo"],
        cliente_id=dados["cliente_id"],
        usuario_id=usuario.id,
        tipo_contrato=dados.get("tipo_contrato"),
        valor_total=dados.get("valor_total"),
        data_inicio=data_ou_erro(dados["data_inicio"]),
        data_fim=data_ou_erro(dados.get("data_fim")),
        status=dados.get("status"),
    )
    db.session.add(contrato)
    salvar()
    return contrato


def atualizar(usuario, id, dados):
    contrato = contrato_do_usuario(id, usuario)

    for campo in CAMPOS_SIMPLES:
        if campo in dados:
            setattr(contrato, campo, dados[campo])

    if "cliente_id" in dados:
        cliente_do_usuario(dados["cliente_id"], usuario)
    if "data_inicio" in dados:
        contrato.data_inicio = data_ou_erro(dados["data_inicio"])
    if "data_fim" in dados:
        contrato.data_fim = data_ou_erro(dados["data_fim"])
    if "valor_total" in dados:
        validar_valor(dados["valor_total"])
    validar_periodo(contrato.data_inicio, contrato.data_fim)

    contrato.updated_at = agora()
    salvar()
    return contrato


def remover(usuario, id):
    db.session.delete(contrato_do_usuario(id, usuario))
    salvar()


def verificar(usuario, id):
    contrato = contrato_do_usuario(id, usuario)
    if contrato.status == STATUS_VERIFICADO:
        raise ErroAplicacao("Este contrato já foi verificado.", 409)

    # O histórico guarda quem verificou (alterado_por) e quando.
    db.session.add(HistoricoStatus(
        contrato_id=contrato.id,
        status_anterior=contrato.status,
        status_novo=STATUS_VERIFICADO,
        alterado_por=usuario.id,
    ))
    contrato.status = STATUS_VERIFICADO
    contrato.updated_at = agora()
    salvar()
    return contrato
