from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import STATUS_PENDENTE, Clausula, Cliente, Contrato
from api.services.clausulas import validar_descricao
from api.services.contratos import validar_periodo, validar_valor
from api.utils import agora, data_ou_erro, texto

MAX_CLAUSULAS = 100


def _validar_formato(dados_cliente, dados_contrato, clausulas):
    if not isinstance(dados_cliente, dict) or not isinstance(dados_contrato, dict):
        raise ErroAplicacao("Formato do formulário inválido.")
    if not isinstance(clausulas, list):
        raise ErroAplicacao("Formato das cláusulas inválido.")
    if len(clausulas) > MAX_CLAUSULAS:
        raise ErroAplicacao(f"O formulário aceita no máximo {MAX_CLAUSULAS} cláusulas.")


def _cliente_do_formulario(usuario, dados_cliente, nome):
    """Reaproveita o cliente se o documento já estiver cadastrado."""
    documento = texto(dados_cliente.get("documento"))
    cliente = (
        Cliente.query.filter_by(documento=documento, usuario_id=usuario.id).first()
        if documento
        else None
    )
    if cliente is None:
        cliente = Cliente(
            nome=nome,
            tipo=texto(dados_cliente.get("tipo")),
            documento=documento,
            email=texto(dados_cliente.get("email")),
            telefone=texto(dados_cliente.get("telefone")),
            usuario_id=usuario.id,
        )
        db.session.add(cliente)
        db.session.flush()
    return cliente


def _proximo_numero():
    """Número automático do contrato, ex.: CT-2026-00001."""
    ano = agora().year
    proximo = (db.session.query(db.func.max(Contrato.id)).scalar() or 0) + 1
    numero = f"CT-{ano}-{proximo:05d}"
    while Contrato.query.filter_by(numero=numero).first():
        proximo += 1
        numero = f"CT-{ano}-{proximo:05d}"
    return numero


def receber(usuario, dados):
    """Cria cliente (ou reaproveita), contrato pendente e cláusulas de uma vez."""
    dados_cliente = dados.get("cliente") or {}
    dados_contrato = dados.get("contrato") or {}
    clausulas = dados.get("clausulas") or []
    _validar_formato(dados_cliente, dados_contrato, clausulas)

    nome = texto(dados_cliente.get("nome"))
    titulo = texto(dados_contrato.get("titulo"))
    if not nome:
        raise ErroAplicacao("Informe o nome do cliente.")
    if not titulo:
        raise ErroAplicacao("Informe o título do contrato.")
    if not dados_contrato.get("data_inicio"):
        raise ErroAplicacao("Informe a data de início.")

    for item in clausulas:
        if not isinstance(item, dict):
            raise ErroAplicacao("Cada cláusula deve ser um objeto JSON.")
        validar_descricao(item.get("descricao"))

    data_inicio = data_ou_erro(dados_contrato.get("data_inicio"))
    data_fim = data_ou_erro(dados_contrato.get("data_fim"))
    validar_periodo(data_inicio, data_fim)
    valor = validar_valor(dados_contrato.get("valor_total"))

    cliente = _cliente_do_formulario(usuario, dados_cliente, nome)
    contrato = Contrato(
        numero=_proximo_numero(),
        titulo=titulo,
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        tipo_contrato=texto(dados_contrato.get("tipo_contrato")),
        valor_total=valor,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=STATUS_PENDENTE,
    )
    db.session.add(contrato)
    db.session.flush()

    for ordem, item in enumerate(clausulas, start=1):
        titulo_clausula = texto(item.get("titulo"))
        descricao = texto(item.get("descricao"))
        if titulo_clausula or descricao:
            db.session.add(Clausula(
                contrato_id=contrato.id,
                titulo=titulo_clausula,
                descricao=descricao,
                ordem=ordem,
            ))

    salvar()
    return contrato
