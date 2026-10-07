from werkzeug.security import check_password_hash, generate_password_hash

from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.models import Usuario
from api.utils import texto


def _usuario_ou_404(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        raise ErroAplicacao("Usuário não encontrado.", 404)
    return usuario


def _por_email(email):
    return Usuario.query.filter(db.func.lower(Usuario.email) == email).first()


def autenticar(dados):
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    if not email or not senha:
        raise ErroAplicacao("Informe e-mail e senha.")

    usuario = _por_email(email)
    if not usuario or not check_password_hash(usuario.senha_hash, senha):
        raise ErroAplicacao("E-mail ou senha incorretos.", 401)
    return usuario


def registrar(dados):
    """Autocadastro: o papel é sempre "usuario", nunca vem do corpo."""
    nome = texto(dados.get("nome"))
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        raise ErroAplicacao("Informe nome, e-mail e senha.")
    if "@" not in email:
        raise ErroAplicacao("E-mail inválido.")
    if len(senha) < 6:
        raise ErroAplicacao("A senha deve ter pelo menos 6 caracteres.")
    if _por_email(email):
        raise ErroAplicacao("Já existe um usuário com este e-mail.", 409)

    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=generate_password_hash(senha),
        papel="usuario",
    )
    db.session.add(usuario)
    salvar()
    return usuario


def listar():
    return Usuario.query.order_by(Usuario.id).all()


def buscar(usuario_atual, id):
    # Quem não é admin só enxerga a si mesmo; os demais respondem 404.
    if usuario_atual.papel != "admin" and usuario_atual.id != id:
        raise ErroAplicacao("Usuário não encontrado.", 404)
    return _usuario_ou_404(id)


def atualizar(id, dados):
    usuario = _usuario_ou_404(id)
    for campo in ["nome", "email"]:
        if campo in dados:
            setattr(usuario, campo, dados[campo])
    if dados.get("senha"):
        usuario.senha_hash = generate_password_hash(dados["senha"])
    salvar()
    return usuario


def remover(id):
    db.session.delete(_usuario_ou_404(id))
    salvar()
