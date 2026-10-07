from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import Aditivo
from api.services.acesso import contrato_do_usuario, item_do_usuario, itens_do_usuario
from api.utils import data_ou_erro

MENSAGEM_NAO_ENCONTRADO = "Aditivo não encontrado."


def listar(usuario, contrato_id=None):
    return itens_do_usuario(Aditivo, usuario, contrato_id).order_by(Aditivo.id).all()


def buscar(usuario, id):
    return item_do_usuario(Aditivo, id, usuario, MENSAGEM_NAO_ENCONTRADO)


def criar(usuario, dados):
    obrigatorios = ["contrato_id", "descricao", "data_assinatura"]
    faltando = [campo for campo in obrigatorios if dados.get(campo) in (None, "")]
    if faltando:
        raise ErroAplicacao(f"Campos obrigatórios: {', '.join(faltando)}.")
    contrato_do_usuario(dados["contrato_id"], usuario)

    aditivo = Aditivo(
        contrato_id=dados["contrato_id"],
        descricao=dados["descricao"],
        novo_valor=dados.get("novo_valor"),
        nova_data_fim=data_ou_erro(dados.get("nova_data_fim")),
        data_assinatura=data_ou_erro(dados["data_assinatura"]),
    )
    db.session.add(aditivo)
    salvar()
    return aditivo


def atualizar(usuario, id, dados):
    aditivo = buscar(usuario, id)
    if "contrato_id" in dados:
        contrato_do_usuario(dados["contrato_id"], usuario)

    for campo in ["contrato_id", "descricao", "novo_valor"]:
        if campo in dados:
            setattr(aditivo, campo, dados[campo])
    if "nova_data_fim" in dados:
        aditivo.nova_data_fim = data_ou_erro(dados["nova_data_fim"])
    if "data_assinatura" in dados:
        aditivo.data_assinatura = data_ou_erro(dados["data_assinatura"])
    salvar()
    return aditivo


def remover(usuario, id):
    db.session.delete(buscar(usuario, id))
    salvar()
