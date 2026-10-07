"""Buscas restritas ao dono: o que é de outro usuário responde 404."""
from api.exceptions import ErroAplicacao
from api.models import Cliente, Contrato


def _ou_404(registro, mensagem):
    if registro is None:
        raise ErroAplicacao(mensagem, 404)
    return registro


def contrato_do_usuario(id, usuario):
    return _ou_404(
        Contrato.query.filter_by(id=id, usuario_id=usuario.id).first(),
        "Contrato não encontrado.",
    )


def cliente_do_usuario(id, usuario):
    return _ou_404(
        Cliente.query.filter_by(id=id, usuario_id=usuario.id).first(),
        "Cliente não encontrado.",
    )


def itens_do_usuario(modelo, usuario, contrato_id=None):
    """Consulta de itens ligados a contratos (cláusula, aditivo, histórico)."""
    consulta = modelo.query.join(Contrato).filter(Contrato.usuario_id == usuario.id)
    if contrato_id is not None:
        consulta = consulta.filter(modelo.contrato_id == contrato_id)
    return consulta


def item_do_usuario(modelo, id, usuario, mensagem):
    return _ou_404(
        itens_do_usuario(modelo, usuario).filter(modelo.id == id).first(),
        mensagem,
    )
