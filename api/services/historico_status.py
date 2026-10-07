from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import HistoricoStatus
from api.services.acesso import contrato_do_usuario, item_do_usuario, itens_do_usuario
from api.utils import agora, datahora_ou_erro

MENSAGEM_NAO_ENCONTRADO = "Histórico de status não encontrado."


def listar(usuario, contrato_id=None):
    return (
        itens_do_usuario(HistoricoStatus, usuario, contrato_id)
        .order_by(HistoricoStatus.id)
        .all()
    )


def buscar(usuario, id):
    return item_do_usuario(HistoricoStatus, id, usuario, MENSAGEM_NAO_ENCONTRADO)


def criar(usuario, dados):
    if dados.get("contrato_id") in (None, ""):
        raise ErroAplicacao("O campo 'contrato_id' é obrigatório.")
    contrato_do_usuario(dados["contrato_id"], usuario)

    historico = HistoricoStatus(
        contrato_id=dados["contrato_id"],
        status_anterior=dados.get("status_anterior"),
        status_novo=dados.get("status_novo"),
        alterado_em=(
            datahora_ou_erro(dados["alterado_em"])
            if dados.get("alterado_em")
            else agora()
        ),
        alterado_por=usuario.id,
    )
    db.session.add(historico)
    salvar()
    return historico


def atualizar(usuario, id, dados):
    historico = buscar(usuario, id)
    if "contrato_id" in dados:
        contrato_do_usuario(dados["contrato_id"], usuario)

    for campo in ["contrato_id", "status_anterior", "status_novo"]:
        if campo in dados:
            setattr(historico, campo, dados[campo])
    if "alterado_em" in dados:
        historico.alterado_em = datahora_ou_erro(dados["alterado_em"])
    salvar()
    return historico


def remover(usuario, id):
    db.session.delete(buscar(usuario, id))
    salvar()
