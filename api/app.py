import os
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_swagger_ui import get_swaggerui_blueprint
from sqlalchemy.exc import IntegrityError
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash
from api import analisar_clausulas as servico_analise_clausulas

load_dotenv()  

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# DATABASE_URL (ex.: "sqlite://" nos testes) tem prioridade sobre as variáveis DB_*.
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Status usados pelo fluxo de verificação (a coluna "status" já existe no banco).
STATUS_PENDENTE = "pendente"
STATUS_VERIFICADO = "verificado"
MAX_CARACTERES_CLAUSULA = 30_000

# Token de login (assinado). Defina SECRET_KEY no .env em produção.
SECRET_KEY = os.getenv("SECRET_KEY") or "chave-apenas-para-desenvolvimento"
TOKEN_VALIDADE_SEGUNDOS = 60 * 60 * 8  # 8 horas
serializer = URLSafeTimedSerializer(SECRET_KEY)


@app.after_request
def liberar_cors(resposta):
    # Permite que o front-end (outra porta/origem) consuma a API.
    resposta.headers["Access-Control-Allow-Origin"] = os.getenv("CORS_ORIGIN", "*")
    resposta.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resposta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resposta


# ============================================================
# SWAGGER
# ============================================================

SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.json"

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "API Flask - Gestão de Contratos"
    }
)

app.register_blueprint(
    swagger_ui_blueprint,
    url_prefix=SWAGGER_URL
)


# ============================================================
# MODELOS
# ============================================================

class Cliente(db.Model):
    __tablename__ = "cliente"
    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id",
            "documento",
            name="uq_cliente_usuario_documento",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String)
    documento = db.Column(db.String)
    email = db.Column(db.String)
    telefone = db.Column(db.String)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contratos = db.relationship("Contrato", back_populates="cliente")
    usuario = db.relationship("Usuario", back_populates="clientes")

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo,
            "documento": self.documento,
            "email": self.email,
            "telefone": self.telefone,
            "created_at": iso(self.created_at),
        }


class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    senha_hash = db.Column(db.String, nullable=False)
    papel = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contratos = db.relationship("Contrato", back_populates="usuario")
    clientes = db.relationship("Cliente", back_populates="usuario")
    alteracoes_status = db.relationship("HistoricoStatus", back_populates="usuario")

    def to_dict(self):
        # O hash da senha não é exposto pela API.
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "papel": self.papel,
            "created_at": iso(self.created_at),
        }


class Contrato(db.Model):
    __tablename__ = "contrato"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String, nullable=False, unique=True)
    titulo = db.Column(db.String, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    tipo_contrato = db.Column(db.String)
    valor_total = db.Column(db.Numeric(12, 2))
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    status = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    cliente = db.relationship("Cliente", back_populates="contratos")
    usuario = db.relationship("Usuario", back_populates="contratos")
    # cascade: ao excluir um contrato, remove cláusulas, aditivos e histórico dele.
    clausulas = db.relationship(
        "Clausula", back_populates="contrato", cascade="all, delete-orphan"
    )
    aditivos = db.relationship(
        "Aditivo", back_populates="contrato", cascade="all, delete-orphan"
    )
    historicos = db.relationship(
        "HistoricoStatus", back_populates="contrato", cascade="all, delete-orphan"
    )
    analise = db.relationship(
        "AnaliseContrato",
        back_populates="contrato",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def dados_verificacao(self):
        """Retorna (nome de quem verificou, data/hora) a partir do histórico."""
        if self.status != STATUS_VERIFICADO:
            return None, None

        registro = (
            HistoricoStatus.query
            .filter_by(contrato_id=self.id, status_novo=STATUS_VERIFICADO)
            .order_by(HistoricoStatus.alterado_em.desc(), HistoricoStatus.id.desc())
            .first()
        )
        if registro is None:
            return None, None

        nome = registro.usuario.nome if registro.usuario else None
        return nome, iso(registro.alterado_em)

    def to_dict(self):
        verificado_por, verificado_em = self.dados_verificacao()
        return {
            "id": self.id,
            "numero": self.numero,
            "titulo": self.titulo,
            "cliente_id": self.cliente_id,
            "tipo_contrato": self.tipo_contrato,
            "valor_total": numero_decimal(self.valor_total),
            "data_inicio": iso(self.data_inicio),
            "data_fim": iso(self.data_fim),
            "status": self.status,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "verificado_por": verificado_por,
            "verificado_em": verificado_em,
        }


class Clausula(db.Model):
    __tablename__ = "clausula"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo = db.Column(db.String)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer)

    contrato = db.relationship("Contrato", back_populates="clausulas")

    def to_dict(self):
        return {
            "id": self.id,
            "contrato_id": self.contrato_id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "ordem": self.ordem,
        }


class Aditivo(db.Model):
    __tablename__ = "aditivo"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descricao = db.Column(db.Text, nullable=False)
    novo_valor = db.Column(db.Numeric(12, 2))
    nova_data_fim = db.Column(db.Date)
    data_assinatura = db.Column(db.Date, nullable=False)

    contrato = db.relationship("Contrato", back_populates="aditivos")

    def to_dict(self):
        return {
            "id": self.id,
            "contrato_id": self.contrato_id,
            "descricao": self.descricao,
            "novo_valor": numero_decimal(self.novo_valor),
            "nova_data_fim": iso(self.nova_data_fim),
            "data_assinatura": iso(self.data_assinatura),
        }


class HistoricoStatus(db.Model):
    __tablename__ = "historico_status"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status_anterior = db.Column(db.String)
    status_novo = db.Column(db.String)
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow)
    alterado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"))

    contrato = db.relationship("Contrato", back_populates="historicos")
    usuario = db.relationship("Usuario", back_populates="alteracoes_status")

    def to_dict(self):
        return {
            "id": self.id,
            "contrato_id": self.contrato_id,
            "status_anterior": self.status_anterior,
            "status_novo": self.status_novo,
            "alterado_em": iso(self.alterado_em),
            "alterado_por": self.alterado_por,
            "alterado_por_nome": self.usuario.nome if self.usuario else None,
        }


class AnaliseContrato(db.Model):
    __tablename__ = "analise_contrato"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contrato.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    texto_hash = db.Column(db.String(64), nullable=False)
    modelo = db.Column(db.String, nullable=False)
    versao_prompt = db.Column(db.String, nullable=False)
    analisado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    contrato = db.relationship("Contrato", back_populates="analise")
    clausulas = db.relationship(
        "ResultadoAnaliseClausula",
        back_populates="analise",
        cascade="all, delete-orphan",
    )


class ResultadoAnaliseClausula(db.Model):
    __tablename__ = "resultado_analise_clausula"

    id = db.Column(db.Integer, primary_key=True)
    analise_id = db.Column(
        db.Integer,
        db.ForeignKey("analise_contrato.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String, nullable=False)
    valor_ou_percentual = db.Column(db.String, nullable=False, default="")
    impacto = db.Column(db.String, nullable=False)
    trecho_original = db.Column(db.Text, nullable=False)
    status_revisao = db.Column(db.String, nullable=False, default="pendente")
    tipo_corrigido = db.Column(db.String)
    valor_corrigido = db.Column(db.String)
    impacto_corrigido = db.Column(db.String)
    revisado_em = db.Column(db.DateTime)

    analise = db.relationship("AnaliseContrato", back_populates="clausulas")

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "valor_ou_percentual": self.valor_ou_percentual,
            "impacto": self.impacto,
            "trecho_original": self.trecho_original,
            "status_revisao": self.status_revisao,
            "tipo_corrigido": self.tipo_corrigido,
            "valor_corrigido": self.valor_corrigido,
            "impacto_corrigido": self.impacto_corrigido,
            "revisado_em": iso(self.revisado_em),
        }


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def iso(valor):
    return valor.isoformat() if valor is not None else None


def numero_decimal(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def parse_date(valor):
    if valor in (None, ""):
        return None
    return datetime.strptime(valor, "%Y-%m-%d").date()


def parse_datetime(valor):
    if valor in (None, ""):
        return None

    # Aceita: 2026-09-07T18:30:00 ou 2026-09-07 18:30:00
    valor = valor.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")


def erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def obter_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return None
    return dados


def salvar():
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        return erro(
            "Não foi possível salvar. Verifique campos únicos e chaves estrangeiras.",
            409,
        )
    return None


# ============================================================
# ROTA INICIAL
# ============================================================

@app.get("/")
def inicio():
    return jsonify({
        "mensagem": "API de contratos funcionando",
        "recursos": [
            "/clientes",
            "/usuarios",
            "/contratos",
            "/clausulas",
            "/aditivos",
            "/historico-status",
            "/swagger/",
        ]
    })


# ============================================================
# CLIENTE - GET / POST / PUT / DELETE
# ============================================================

@app.get("/clientes")
def listar_clientes():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    clientes = (
        Cliente.query.filter_by(usuario_id=usuario.id)
        .order_by(Cliente.id)
        .all()
    )
    return jsonify([cliente.to_dict() for cliente in clientes])


@app.get("/clientes/<int:id>")
def buscar_cliente(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    cliente = Cliente.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not cliente:
        return erro("Cliente não encontrado.", 404)
    return jsonify(cliente.to_dict())


@app.post("/clientes")
def criar_cliente():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    if not dados.get("nome"):
        return erro("O campo 'nome' é obrigatório.")

    documento = texto(dados.get("documento"))
    if documento and Cliente.query.filter_by(
        documento=documento, usuario_id=usuario.id
    ).first():
        return erro("Não foi possível cadastrar este cliente com os dados informados.", 409)

    cliente = Cliente(
        nome=dados["nome"],
        tipo=dados.get("tipo"),
        documento=documento,
        email=dados.get("email"),
        telefone=dados.get("telefone"),
        usuario_id=usuario.id,
    )

    db.session.add(cliente)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(cliente.to_dict()), 201


@app.put("/clientes/<int:id>")
def atualizar_cliente(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    cliente = Cliente.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not cliente:
        return erro("Cliente não encontrado.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    for campo in ["nome", "tipo", "documento", "email", "telefone"]:
        if campo in dados:
            setattr(cliente, campo, dados[campo])

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(cliente.to_dict())


@app.delete("/clientes/<int:id>")
def deletar_cliente(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    cliente = Cliente.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not cliente:
        return erro("Cliente não encontrado.", 404)

    db.session.delete(cliente)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({"mensagem": "Cliente removido com sucesso."})


# ============================================================
# USUÁRIO - GET / POST / PUT / DELETE
# ============================================================

@app.get("/usuarios")
def listar_usuarios():
    usuario_atual = usuario_autenticado()
    if not usuario_atual:
        return erro("Autenticação necessária.", 401)
    if usuario_atual.papel != "admin":
        return erro("Permissão de administrador necessária.", 403)

    usuarios = Usuario.query.order_by(Usuario.id).all()
    return jsonify([usuario.to_dict() for usuario in usuarios])


@app.get("/usuarios/<int:id>")
def buscar_usuario(id):
    usuario_atual = usuario_autenticado()
    if not usuario_atual:
        return erro("Autenticação necessária.", 401)
    if usuario_atual.papel != "admin" and usuario_atual.id != id:
        return erro("Usuário não encontrado.", 404)

    usuario = db.session.get(Usuario, id)
    if not usuario:
        return erro("Usuário não encontrado.", 404)
    return jsonify(usuario.to_dict())


@app.post("/usuarios")
def criar_usuario():
    return erro("Use o endpoint /auth/registrar para criar uma conta.", 405)


@app.put("/usuarios/<int:id>")
def atualizar_usuario(id):
    usuario_atual = usuario_autenticado()
    if not usuario_atual:
        return erro("Autenticação necessária.", 401)
    if usuario_atual.papel != "admin":
        return erro("Permissão de administrador necessária.", 403)

    usuario = db.session.get(Usuario, id)
    if not usuario:
        return erro("Usuário não encontrado.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    for campo in ["nome", "email"]:
        if campo in dados:
            setattr(usuario, campo, dados[campo])

    if "senha" in dados and dados["senha"]:
        usuario.senha_hash = generate_password_hash(dados["senha"])

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(usuario.to_dict())


@app.delete("/usuarios/<int:id>")
def deletar_usuario(id):
    usuario_atual = usuario_autenticado()
    if not usuario_atual:
        return erro("Autenticação necessária.", 401)
    if usuario_atual.papel != "admin":
        return erro("Permissão de administrador necessária.", 403)

    usuario = db.session.get(Usuario, id)
    if not usuario:
        return erro("Usuário não encontrado.", 404)

    db.session.delete(usuario)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({"mensagem": "Usuário removido com sucesso."})


# ============================================================
# CONTRATO - GET / POST / PUT / DELETE
# ============================================================

@app.get("/contratos")
def listar_contratos():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    pagina = request.args.get("page", default=1, type=int)
    por_pagina = request.args.get("per_page", default=50, type=int)
    if pagina < 1 or por_pagina < 1:
        return erro("page e per_page devem ser inteiros positivos.")
    por_pagina = min(por_pagina, 100)

    consulta = Contrato.query.filter_by(usuario_id=usuario.id)
    status = texto(request.args.get("status"))
    tipo = texto(request.args.get("tipo_contrato"))
    busca = texto(request.args.get("q"))
    if status:
        consulta = consulta.filter(Contrato.status == status)
    if tipo:
        consulta = consulta.filter(Contrato.tipo_contrato == tipo)
    if busca:
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
    return jsonify({
        "items": [contrato.to_dict() for contrato in contratos],
        "pagination": {
            "page": pagina,
            "per_page": por_pagina,
            "total": total,
            "pages": (total + por_pagina - 1) // por_pagina,
        },
    })


@app.get("/contratos/<int:id>")
def buscar_contrato(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)
    return jsonify(contrato.to_dict())


@app.post("/contratos")
def criar_contrato():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    obrigatorios = ["numero", "titulo", "cliente_id", "data_inicio"]
    faltando = [campo for campo in obrigatorios if dados.get(campo) in (None, "")]
    if faltando:
        return erro(f"Campos obrigatórios: {', '.join(faltando)}.")

    cliente = Cliente.query.filter_by(
        id=dados["cliente_id"], usuario_id=usuario.id
    ).first()
    if not cliente:
        return erro("Cliente não encontrado.", 404)

    try:
        contrato = Contrato(
            numero=dados["numero"],
            titulo=dados["titulo"],
            cliente_id=dados["cliente_id"],
            usuario_id=usuario.id,
            tipo_contrato=dados.get("tipo_contrato"),
            valor_total=dados.get("valor_total"),
            data_inicio=parse_date(dados["data_inicio"]),
            data_fim=parse_date(dados.get("data_fim")),
            status=dados.get("status"),
        )
    except (ValueError, TypeError):
        return erro("Datas devem usar o formato YYYY-MM-DD.")

    db.session.add(contrato)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(contrato.to_dict()), 201


@app.put("/contratos/<int:id>")
def atualizar_contrato(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    campos_simples = [
        "numero",
        "titulo",
        "cliente_id",
        "tipo_contrato",
        "valor_total",
        "status",
    ]

    for campo in campos_simples:
        if campo in dados:
            setattr(contrato, campo, dados[campo])

    if "cliente_id" in dados:
        cliente = Cliente.query.filter_by(
            id=dados["cliente_id"], usuario_id=usuario.id
        ).first()
        if not cliente:
            return erro("Cliente não encontrado.", 404)

    try:
        if "data_inicio" in dados:
            contrato.data_inicio = parse_date(dados["data_inicio"])
        if "data_fim" in dados:
            contrato.data_fim = parse_date(dados["data_fim"])
    except (ValueError, TypeError):
        return erro("Datas devem usar o formato YYYY-MM-DD.")

    if "valor_total" in dados and dados["valor_total"] not in (None, ""):
        try:
            if Decimal(str(dados["valor_total"])) < 0:
                db.session.rollback()
                return erro("O valor total não pode ser negativo.")
        except InvalidOperation:
            db.session.rollback()
            return erro("Valor total inválido.")

    if (
        contrato.data_fim
        and contrato.data_inicio
        and contrato.data_fim < contrato.data_inicio
    ):
        db.session.rollback()
        return erro("A data de término não pode ser anterior ao início.")

    contrato.updated_at = datetime.utcnow()

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(contrato.to_dict())


@app.delete("/contratos/<int:id>")
def deletar_contrato(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    db.session.delete(contrato)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({"mensagem": "Contrato removido com sucesso."})


# ============================================================
# CLÁUSULA - GET / POST / PUT / DELETE
# ============================================================

@app.get("/clausulas")
def listar_clausulas():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    clausulas = (
        filtrar_por_contrato(
            Clausula.query.join(Contrato)
            .filter(Contrato.usuario_id == usuario.id),
            Clausula,
        )
        .order_by(Clausula.ordem, Clausula.id)
        .all()
    )
    return jsonify([clausula.to_dict() for clausula in clausulas])


@app.get("/clausulas/<int:id>")
def buscar_clausula(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    clausula = (
        Clausula.query.join(Contrato)
        .filter(Clausula.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not clausula:
        return erro("Cláusula não encontrada.", 404)
    return jsonify(clausula.to_dict())


@app.post("/clausulas")
def criar_clausula():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    if dados.get("contrato_id") in (None, ""):
        return erro("O campo 'contrato_id' é obrigatório.")

    contrato = Contrato.query.filter_by(
        id=dados["contrato_id"], usuario_id=usuario.id
    ).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    descricao = dados.get("descricao")
    if descricao is not None and not isinstance(descricao, str):
        return erro("A descrição da cláusula deve ser texto.")
    if descricao is not None and len(descricao) > MAX_CARACTERES_CLAUSULA:
        return erro(
            f"A descrição da cláusula excede {MAX_CARACTERES_CLAUSULA} caracteres."
        )

    clausula = Clausula(
        contrato_id=dados["contrato_id"],
        titulo=dados.get("titulo"),
        descricao=descricao,
        ordem=dados.get("ordem"),
    )

    db.session.add(clausula)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(clausula.to_dict()), 201


@app.put("/clausulas/<int:id>")
def atualizar_clausula(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    clausula = (
        Clausula.query.join(Contrato)
        .filter(Clausula.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not clausula:
        return erro("Cláusula não encontrada.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    if "contrato_id" in dados:
        contrato = Contrato.query.filter_by(
            id=dados["contrato_id"], usuario_id=usuario.id
        ).first()
        if not contrato:
            return erro("Contrato não encontrado.", 404)

    if "descricao" in dados:
        descricao = dados["descricao"]
        if descricao is not None and not isinstance(descricao, str):
            return erro("A descrição da cláusula deve ser texto.")
        if descricao is not None and len(descricao) > MAX_CARACTERES_CLAUSULA:
            return erro(
                f"A descrição da cláusula excede {MAX_CARACTERES_CLAUSULA} caracteres."
            )

    for campo in ["contrato_id", "titulo", "descricao", "ordem"]:
        if campo in dados:
            setattr(clausula, campo, dados[campo])

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(clausula.to_dict())


@app.delete("/clausulas/<int:id>")
def deletar_clausula(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    clausula = (
        Clausula.query.join(Contrato)
        .filter(Clausula.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not clausula:
        return erro("Cláusula não encontrada.", 404)

    db.session.delete(clausula)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({"mensagem": "Cláusula removida com sucesso."})


# ============================================================
# ADITIVO - GET / POST / PUT / DELETE
# ============================================================

@app.get("/aditivos")
def listar_aditivos():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    aditivos = (
        filtrar_por_contrato(
            Aditivo.query.join(Contrato)
            .filter(Contrato.usuario_id == usuario.id),
            Aditivo,
        )
        .order_by(Aditivo.id)
        .all()
    )
    return jsonify([aditivo.to_dict() for aditivo in aditivos])


@app.get("/aditivos/<int:id>")
def buscar_aditivo(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    aditivo = (
        Aditivo.query.join(Contrato)
        .filter(Aditivo.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not aditivo:
        return erro("Aditivo não encontrado.", 404)
    return jsonify(aditivo.to_dict())


@app.post("/aditivos")
def criar_aditivo():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    obrigatorios = ["contrato_id", "descricao", "data_assinatura"]
    faltando = [campo for campo in obrigatorios if dados.get(campo) in (None, "")]
    if faltando:
        return erro(f"Campos obrigatórios: {', '.join(faltando)}.")

    contrato = Contrato.query.filter_by(
        id=dados["contrato_id"], usuario_id=usuario.id
    ).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    try:
        aditivo = Aditivo(
            contrato_id=dados["contrato_id"],
            descricao=dados["descricao"],
            novo_valor=dados.get("novo_valor"),
            nova_data_fim=parse_date(dados.get("nova_data_fim")),
            data_assinatura=parse_date(dados["data_assinatura"]),
        )
    except (ValueError, TypeError):
        return erro("Datas devem usar o formato YYYY-MM-DD.")

    db.session.add(aditivo)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(aditivo.to_dict()), 201


@app.put("/aditivos/<int:id>")
def atualizar_aditivo(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    aditivo = (
        Aditivo.query.join(Contrato)
        .filter(Aditivo.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not aditivo:
        return erro("Aditivo não encontrado.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    if "contrato_id" in dados:
        contrato = Contrato.query.filter_by(
            id=dados["contrato_id"], usuario_id=usuario.id
        ).first()
        if not contrato:
            return erro("Contrato não encontrado.", 404)

    for campo in ["contrato_id", "descricao", "novo_valor"]:
        if campo in dados:
            setattr(aditivo, campo, dados[campo])

    try:
        if "nova_data_fim" in dados:
            aditivo.nova_data_fim = parse_date(dados["nova_data_fim"])
        if "data_assinatura" in dados:
            aditivo.data_assinatura = parse_date(dados["data_assinatura"])
    except (ValueError, TypeError):
        return erro("Datas devem usar o formato YYYY-MM-DD.")

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(aditivo.to_dict())


@app.delete("/aditivos/<int:id>")
def deletar_aditivo(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    aditivo = (
        Aditivo.query.join(Contrato)
        .filter(Aditivo.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not aditivo:
        return erro("Aditivo não encontrado.", 404)

    db.session.delete(aditivo)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({"mensagem": "Aditivo removido com sucesso."})


# ============================================================
# HISTÓRICO DE STATUS - GET / POST / PUT / DELETE
# ============================================================

@app.get("/historico-status")
def listar_historico_status():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    historicos = (
        filtrar_por_contrato(
            HistoricoStatus.query.join(Contrato)
            .filter(Contrato.usuario_id == usuario.id),
            HistoricoStatus,
        )
        .order_by(HistoricoStatus.id)
        .all()
    )
    return jsonify([historico.to_dict() for historico in historicos])


@app.get("/historico-status/<int:id>")
def buscar_historico_status(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    historico = (
        HistoricoStatus.query.join(Contrato)
        .filter(HistoricoStatus.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not historico:
        return erro("Histórico de status não encontrado.", 404)
    return jsonify(historico.to_dict())


@app.post("/historico-status")
def criar_historico_status():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    if dados.get("contrato_id") in (None, ""):
        return erro("O campo 'contrato_id' é obrigatório.")

    contrato = Contrato.query.filter_by(
        id=dados["contrato_id"], usuario_id=usuario.id
    ).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    try:
        historico = HistoricoStatus(
            contrato_id=dados["contrato_id"],
            status_anterior=dados.get("status_anterior"),
            status_novo=dados.get("status_novo"),
            alterado_em=(
                parse_datetime(dados["alterado_em"])
                if dados.get("alterado_em")
                else datetime.utcnow()
            ),
            alterado_por=usuario.id,
        )
    except (ValueError, TypeError):
        return erro("Use uma data/hora ISO, por exemplo 2026-09-07T18:30:00.")

    db.session.add(historico)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(historico.to_dict()), 201


@app.put("/historico-status/<int:id>")
def atualizar_historico_status(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    historico = (
        HistoricoStatus.query.join(Contrato)
        .filter(HistoricoStatus.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not historico:
        return erro("Histórico de status não encontrado.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    if "contrato_id" in dados:
        contrato = Contrato.query.filter_by(
            id=dados["contrato_id"], usuario_id=usuario.id
        ).first()
        if not contrato:
            return erro("Contrato não encontrado.", 404)

    for campo in [
        "contrato_id",
        "status_anterior",
        "status_novo",
    ]:
        if campo in dados:
            setattr(historico, campo, dados[campo])

    try:
        if "alterado_em" in dados:
            historico.alterado_em = parse_datetime(dados["alterado_em"])
    except (ValueError, TypeError):
        return erro("Use uma data/hora ISO, por exemplo 2026-09-07T18:30:00.")

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(historico.to_dict())


@app.delete("/historico-status/<int:id>")
def deletar_historico_status(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    historico = (
        HistoricoStatus.query.join(Contrato)
        .filter(HistoricoStatus.id == id, Contrato.usuario_id == usuario.id)
        .first()
    )
    if not historico:
        return erro("Histórico de status não encontrado.", 404)

    db.session.delete(historico)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({"mensagem": "Histórico de status removido com sucesso."})


# ============================================================
# FILTRO POR CONTRATO (?contrato_id=)
# ============================================================

def filtrar_por_contrato(consulta, modelo):
    contrato_id = request.args.get("contrato_id", type=int)
    if contrato_id is not None:
        consulta = consulta.filter(modelo.contrato_id == contrato_id)
    return consulta


def texto(valor):
    """Devolve a string sem espaços sobrando, ou None se vazia."""
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


# ============================================================
# AUTENTICAÇÃO - /auth/login, /auth/registrar, /auth/me
# ============================================================

def gerar_token(usuario):
    return serializer.dumps({"id": usuario.id})


def usuario_autenticado():
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None
    try:
        dados = serializer.loads(cabecalho[7:], max_age=TOKEN_VALIDADE_SEGUNDOS)
    except BadSignature:
        return None
    return db.session.get(Usuario, dados.get("id"))


@app.post("/auth/login")
def login():
    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    if not email or not senha:
        return erro("Informe e-mail e senha.")

    usuario = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()
    if not usuario or not check_password_hash(usuario.senha_hash, senha):
        return erro("E-mail ou senha incorretos.", 401)

    return jsonify({"token": gerar_token(usuario), "usuario": usuario.to_dict()})


@app.post("/auth/registrar")
def registrar():
    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    nome = texto(dados.get("nome"))
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        return erro("Informe nome, e-mail e senha.")
    if "@" not in email:
        return erro("E-mail inválido.")
    if len(senha) < 6:
        return erro("A senha deve ter pelo menos 6 caracteres.")

    if Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
        return erro("Já existe um usuário com este e-mail.", 409)

    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=generate_password_hash(senha),
        papel="usuario",
    )
    db.session.add(usuario)
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(usuario.to_dict()), 201


@app.get("/auth/me")
def perfil():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Sessão inválida ou expirada.", 401)
    return jsonify(usuario.to_dict())


@app.get("/dashboard/resumo")
def resumo_dashboard():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    consulta_contratos = Contrato.query.filter_by(usuario_id=usuario.id)
    hoje = datetime.utcnow().date()
    limite_vencimento = hoje.fromordinal(hoje.toordinal() + 30)

    total_contratos = consulta_contratos.count()
    valor_total = (
        db.session.query(db.func.coalesce(db.func.sum(Contrato.valor_total), 0))
        .filter(Contrato.usuario_id == usuario.id)
        .scalar()
    )
    verificados = consulta_contratos.filter_by(status=STATUS_VERIFICADO).count()
    vencendo_em_30_dias = consulta_contratos.filter(
        Contrato.data_fim >= hoje,
        Contrato.data_fim <= limite_vencimento,
    ).count()
    aditivos = (
        Aditivo.query.join(Contrato)
        .filter(Contrato.usuario_id == usuario.id)
        .count()
    )
    contratos_por_tipo = (
        db.session.query(
            Contrato.tipo_contrato,
            db.func.count(Contrato.id),
        )
        .filter(Contrato.usuario_id == usuario.id)
        .group_by(Contrato.tipo_contrato)
        .order_by(Contrato.tipo_contrato)
        .all()
    )

    clausulas_alto_impacto = (
        db.session.query(db.func.count(ResultadoAnaliseClausula.id))
        .join(AnaliseContrato)
        .join(Contrato)
        .filter(
            Contrato.usuario_id == usuario.id,
            ResultadoAnaliseClausula.status_revisao != "descartada",
            db.func.coalesce(
                ResultadoAnaliseClausula.impacto_corrigido,
                ResultadoAnaliseClausula.impacto,
            ) == "alto",
        )
        .scalar()
    )

    return jsonify({
        "clausulas_alto_impacto": clausulas_alto_impacto,
        "total_contratos": total_contratos,
        "contratos_pendentes": total_contratos - verificados,
        "contratos_verificados": verificados,
        "valor_total": numero_decimal(valor_total),
        "vencendo_em_30_dias": vencendo_em_30_dias,
        "total_aditivos": aditivos,
        "contratos_por_tipo": [
            {"tipo": tipo or "Não informado", "total": total}
            for tipo, total in contratos_por_tipo
        ],
    })


# ============================================================
# VERIFICAÇÃO DE CONTRATO (exige login)
# ============================================================

@app.post("/contratos/<int:id>/verificar")
def verificar_contrato(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    if contrato.status == STATUS_VERIFICADO:
        return erro("Este contrato já foi verificado.", 409)

    # O histórico guarda quem verificou (alterado_por) e quando.
    db.session.add(HistoricoStatus(
        contrato_id=contrato.id,
        status_anterior=contrato.status,
        status_novo=STATUS_VERIFICADO,
        alterado_por=usuario.id,
    ))
    contrato.status = STATUS_VERIFICADO
    contrato.updated_at = datetime.utcnow()

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify(contrato.to_dict())


@app.post("/contratos/<int:id>/analisar")
def analisar_contrato(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)

    descricoes = [
        clausula.descricao.strip()
        for clausula in sorted(contrato.clausulas, key=lambda item: (item.ordem or 0, item.id))
        if clausula.descricao and clausula.descricao.strip()
    ]
    texto = "\n".join(descricoes)
    if not texto:
        return erro("Adicione texto às cláusulas antes de solicitar a análise.", 400)

    texto_hash = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    analise = contrato.analise
    if analise and analise.texto_hash == texto_hash:
        return jsonify({
            "clausulas": [clausula.to_dict() for clausula in analise.clausulas],
            "modelo": analise.modelo,
            "versao_prompt": analise.versao_prompt,
            "reutilizada": True,
        })

    try:
        resultado = servico_analise_clausulas.analisar_clausulas(texto)
    except servico_analise_clausulas.TextoClausulasInvalido as exc:
        return erro(str(exc), 422)
    except servico_analise_clausulas.ErroAnaliseClausulas as exc:
        return erro(str(exc), 502)

    if analise is None:
        analise = AnaliseContrato(contrato=contrato)
        db.session.add(analise)
    else:
        analise.clausulas.clear()

    analise.texto_hash = texto_hash
    analise.modelo = resultado["modelo"]
    analise.versao_prompt = resultado["versao_prompt"]
    analise.analisado_em = datetime.utcnow()
    analise.clausulas.extend(
        ResultadoAnaliseClausula(**clausula)
        for clausula in resultado["clausulas"]
    )

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({
        "clausulas": [clausula.to_dict() for clausula in analise.clausulas],
        "modelo": analise.modelo,
        "versao_prompt": analise.versao_prompt,
        "reutilizada": False,
    }), 201


@app.get("/contratos/<int:id>/analise")
def buscar_analise_contrato(id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)
    if not contrato.analise:
        return erro("Este contrato ainda não possui análise.", 404)

    return jsonify({
        "clausulas": [clausula.to_dict() for clausula in contrato.analise.clausulas],
        "modelo": contrato.analise.modelo,
        "versao_prompt": contrato.analise.versao_prompt,
        "analisado_em": iso(contrato.analise.analisado_em),
    })


@app.put("/contratos/<int:id>/analise/<int:clausula_id>")
def revisar_analise_clausula(id, clausula_id):
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    contrato = Contrato.query.filter_by(id=id, usuario_id=usuario.id).first()
    if not contrato:
        return erro("Contrato não encontrado.", 404)
    resultado = ResultadoAnaliseClausula.query.join(AnaliseContrato).filter(
        AnaliseContrato.contrato_id == contrato.id,
        ResultadoAnaliseClausula.id == clausula_id,
    ).first()
    if not resultado:
        return erro("Cláusula analisada não encontrada.", 404)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")
    acao = dados.get("acao")
    if acao not in {"confirmar", "corrigir", "descartar"}:
        return erro("A ação deve ser confirmar, corrigir ou descartar.")

    if acao == "corrigir":
        tipo = texto(dados.get("tipo"))
        valor = dados.get("valor_ou_percentual", "")
        impacto = dados.get("impacto")
        if not tipo or len(tipo) > 120:
            return erro("Informe um tipo válido de até 120 caracteres.")
        if not isinstance(valor, str) or len(valor) > 200:
            return erro("O valor ou percentual deve ter até 200 caracteres.")
        if impacto not in servico_analise_clausulas.IMPACTOS_VALIDOS:
            return erro("Impacto inválido. Use baixo, médio ou alto.")
        resultado.tipo_corrigido = tipo
        resultado.valor_corrigido = valor.strip()
        resultado.impacto_corrigido = impacto

    resultado.status_revisao = {
        "confirmar": "confirmada",
        "corrigir": "corrigida",
        "descartar": "descartada",
    }[acao]
    resultado.revisado_em = datetime.utcnow()
    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro
    return jsonify(resultado.to_dict())


# ============================================================
# FORMULÁRIO PÚBLICO DO CLIENTE (cria cliente + contrato + cláusulas)
# ============================================================

@app.post("/formulario")
def receber_formulario():
    usuario = usuario_autenticado()
    if not usuario:
        return erro("Autenticação necessária.", 401)

    dados = obter_json()
    if dados is None:
        return erro("Envie um JSON válido.")

    dados_cliente = dados.get("cliente") or {}
    dados_contrato = dados.get("contrato") or {}
    clausulas = dados.get("clausulas") or []

    if not isinstance(dados_cliente, dict) or not isinstance(dados_contrato, dict):
        return erro("Formato do formulário inválido.")
    if not isinstance(clausulas, list):
        return erro("Formato das cláusulas inválido.")
    if len(clausulas) > 100:
        return erro("O formulário aceita no máximo 100 cláusulas.")

    nome = texto(dados_cliente.get("nome"))
    titulo = texto(dados_contrato.get("titulo"))

    if not nome:
        return erro("Informe o nome do cliente.")
    if not titulo:
        return erro("Informe o título do contrato.")
    if not dados_contrato.get("data_inicio"):
        return erro("Informe a data de início.")

    for item in clausulas:
        if not isinstance(item, dict):
            return erro("Cada cláusula deve ser um objeto JSON.")
        descricao = item.get("descricao")
        if descricao is not None and not isinstance(descricao, str):
            return erro("A descrição da cláusula deve ser texto.")
        if descricao is not None and len(descricao) > MAX_CARACTERES_CLAUSULA:
            return erro(
                f"A descrição da cláusula excede {MAX_CARACTERES_CLAUSULA} caracteres."
            )

    try:
        data_inicio = parse_date(dados_contrato.get("data_inicio"))
        data_fim = parse_date(dados_contrato.get("data_fim"))
    except (ValueError, TypeError):
        return erro("Datas devem usar o formato YYYY-MM-DD.")

    if data_fim and data_fim < data_inicio:
        return erro("A data de término não pode ser anterior ao início.")

    valor = dados_contrato.get("valor_total")
    if valor in (None, ""):
        valor = None
    else:
        try:
            valor = Decimal(str(valor))
        except InvalidOperation:
            return erro("Valor total inválido.")
        if valor < 0:
            return erro("O valor total não pode ser negativo.")

    # Reaproveita o cliente se o documento já estiver cadastrado.
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

    # Número do contrato gerado automaticamente: CT-2026-00001
    ano = datetime.utcnow().year
    proximo = (db.session.query(db.func.max(Contrato.id)).scalar() or 0) + 1
    numero = f"CT-{ano}-{proximo:05d}"
    while Contrato.query.filter_by(numero=numero).first():
        proximo += 1
        numero = f"CT-{ano}-{proximo:05d}"

    contrato = Contrato(
        numero=numero,
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
        if not isinstance(item, dict):
            continue
        titulo_clausula = texto(item.get("titulo"))
        descricao = texto(item.get("descricao"))
        if titulo_clausula or descricao:
            db.session.add(Clausula(
                contrato_id=contrato.id,
                titulo=titulo_clausula,
                descricao=descricao,
                ordem=ordem,
            ))

    resposta_erro = salvar()
    if resposta_erro:
        return resposta_erro

    return jsonify({
        "mensagem": "Formulário recebido com sucesso.",
        "contrato": contrato.to_dict(),
    }), 201


# ============================================================
# TRATAMENTO DE ERROS
# ============================================================

@app.errorhandler(404)
def rota_nao_encontrada(_):
    return erro("Rota não encontrada.", 404)


@app.errorhandler(500)
def erro_interno(_):
    db.session.rollback()
    return erro("Erro interno do servidor.", 500)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    if not os.getenv("SECRET_KEY"):
        print("AVISO: defina SECRET_KEY no .env; usando chave de desenvolvimento.")
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=5000,
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
