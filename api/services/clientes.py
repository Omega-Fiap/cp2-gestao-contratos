from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import Cliente
from api.services.acesso import cliente_do_usuario
from api.utils import texto

CAMPOS_ATUALIZAVEIS = ["nome", "tipo", "documento", "email", "telefone"]


def listar(usuario):
    return (
        Cliente.query.filter_by(usuario_id=usuario.id).order_by(Cliente.id).all()
    )


def criar(usuario, dados):
    if not dados.get("nome"):
        raise ErroAplicacao("O campo 'nome' é obrigatório.")

    documento = texto(dados.get("documento"))
    if documento and Cliente.query.filter_by(
        documento=documento, usuario_id=usuario.id
    ).first():
        raise ErroAplicacao(
            "Não foi possível cadastrar este cliente com os dados informados.", 409
        )

    cliente = Cliente(
        nome=dados["nome"],
        tipo=dados.get("tipo"),
        documento=documento,
        email=dados.get("email"),
        telefone=dados.get("telefone"),
        usuario_id=usuario.id,
    )
    db.session.add(cliente)
    salvar()
    return cliente


def atualizar(usuario, id, dados):
    cliente = cliente_do_usuario(id, usuario)
    for campo in CAMPOS_ATUALIZAVEIS:
        if campo in dados:
            setattr(cliente, campo, dados[campo])
    salvar()
    return cliente


def remover(usuario, id):
    db.session.delete(cliente_do_usuario(id, usuario))
    salvar()
