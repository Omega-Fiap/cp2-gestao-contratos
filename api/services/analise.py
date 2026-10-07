import hashlib

from api.exceptions import ErroAplicacao
from api.extensions import db, salvar
from api.integrations import gemini
from api.models import AnaliseContrato, ResultadoAnaliseClausula
from api.services.acesso import contrato_do_usuario
from api.utils import agora, iso, texto

ACOES_REVISAO = {
    "confirmar": "confirmada",
    "corrigir": "corrigida",
    "descartar": "descartada",
}


def _resposta(analise, **extras):
    return {
        "clausulas": [clausula.to_dict() for clausula in analise.clausulas],
        "modelo": analise.modelo,
        "versao_prompt": analise.versao_prompt,
        **extras,
    }


def _texto_das_clausulas(contrato):
    ordenadas = sorted(contrato.clausulas, key=lambda item: (item.ordem or 0, item.id))
    return "\n".join(
        clausula.descricao.strip()
        for clausula in ordenadas
        if clausula.descricao and clausula.descricao.strip()
    )


def analisar(usuario, id):
    """Devolve (resposta, status HTTP). Reaproveita a análise se o texto não mudou."""
    contrato = contrato_do_usuario(id, usuario)

    conteudo = _texto_das_clausulas(contrato)
    if not conteudo:
        raise ErroAplicacao("Adicione texto às cláusulas antes de solicitar a análise.")

    texto_hash = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    analise = contrato.analise
    if analise and analise.texto_hash == texto_hash:
        return _resposta(analise, reutilizada=True), 200

    try:
        resultado = gemini.analisar_clausulas(conteudo)
    except gemini.TextoClausulasInvalido as exc:
        raise ErroAplicacao(str(exc), 422)
    except gemini.ErroAnaliseClausulas as exc:
        raise ErroAplicacao(str(exc), 502)

    if analise is None:
        analise = AnaliseContrato(contrato=contrato)
        db.session.add(analise)
    else:
        analise.clausulas.clear()

    analise.texto_hash = texto_hash
    analise.modelo = resultado["modelo"]
    analise.versao_prompt = resultado["versao_prompt"]
    analise.analisado_em = agora()
    analise.clausulas.extend(
        ResultadoAnaliseClausula(**clausula) for clausula in resultado["clausulas"]
    )
    salvar()
    return _resposta(analise, reutilizada=False), 201


def buscar(usuario, id):
    contrato = contrato_do_usuario(id, usuario)
    if not contrato.analise:
        raise ErroAplicacao("Este contrato ainda não possui análise.", 404)
    return _resposta(contrato.analise, analisado_em=iso(contrato.analise.analisado_em))


def revisar(usuario, id, clausula_id, dados):
    contrato = contrato_do_usuario(id, usuario)
    resultado = ResultadoAnaliseClausula.query.join(AnaliseContrato).filter(
        AnaliseContrato.contrato_id == contrato.id,
        ResultadoAnaliseClausula.id == clausula_id,
    ).first()
    if not resultado:
        raise ErroAplicacao("Cláusula analisada não encontrada.", 404)

    acao = dados.get("acao")
    if acao not in ACOES_REVISAO:
        raise ErroAplicacao("A ação deve ser confirmar, corrigir ou descartar.")

    if acao == "corrigir":
        tipo = texto(dados.get("tipo"))
        valor = dados.get("valor_ou_percentual", "")
        impacto = dados.get("impacto")
        if not tipo or len(tipo) > 120:
            raise ErroAplicacao("Informe um tipo válido de até 120 caracteres.")
        if not isinstance(valor, str) or len(valor) > 200:
            raise ErroAplicacao("O valor ou percentual deve ter até 200 caracteres.")
        if impacto not in gemini.IMPACTOS_VALIDOS:
            raise ErroAplicacao("Impacto inválido. Use baixo, médio ou alto.")
        resultado.tipo_corrigido = tipo
        resultado.valor_corrigido = valor.strip()
        resultado.impacto_corrigido = impacto

    resultado.status_revisao = ACOES_REVISAO[acao]
    resultado.revisado_em = agora()
    salvar()
    return resultado
