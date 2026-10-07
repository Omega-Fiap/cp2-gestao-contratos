from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import Clausula
from api.services.acesso import contrato_do_usuario, item_do_usuario, itens_do_usuario

MAX_CARACTERES_CLAUSULA = 30_000
MENSAGEM_NAO_ENCONTRADA = "Cláusula não encontrada."


def validar_descricao(descricao):
    if descricao is None:
        return
    if not isinstance(descricao, str):
        raise ErroAplicacao("A descrição da cláusula deve ser texto.")
    if len(descricao) > MAX_CARACTERES_CLAUSULA:
        raise ErroAplicacao(
            f"A descrição da cláusula excede {MAX_CARACTERES_CLAUSULA} caracteres."
        )


def listar(usuario, contrato_id=None):
    return (
        itens_do_usuario(Clausula, usuario, contrato_id)
        .order_by(Clausula.ordem, Clausula.id)
        .all()
    )


def buscar(usuario, id):
    return item_do_usuario(Clausula, id, usuario, MENSAGEM_NAO_ENCONTRADA)


def criar(usuario, dados):
    if dados.get("contrato_id") in (None, ""):
        raise ErroAplicacao("O campo 'contrato_id' é obrigatório.")
    contrato_do_usuario(dados["contrato_id"], usuario)
    validar_descricao(dados.get("descricao"))

    clausula = Clausula(
        contrato_id=dados["contrato_id"],
        titulo=dados.get("titulo"),
        descricao=dados.get("descricao"),
        ordem=dados.get("ordem"),
    )
    db.session.add(clausula)
    salvar()
    return clausula


def atualizar(usuario, id, dados):
    clausula = buscar(usuario, id)
    if "contrato_id" in dados:
        contrato_do_usuario(dados["contrato_id"], usuario)
    if "descricao" in dados:
        validar_descricao(dados["descricao"])

    for campo in ["contrato_id", "titulo", "descricao", "ordem"]:
        if campo in dados:
            setattr(clausula, campo, dados[campo])
    salvar()
    return clausula


def remover(usuario, id):
    db.session.delete(buscar(usuario, id))
    salvar()
