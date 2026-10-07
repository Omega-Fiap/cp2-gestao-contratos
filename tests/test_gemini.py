import json
from urllib.error import HTTPError

import pytest

from api.integrations import gemini as modulo

TEXTO = "A rescisão antecipada gera multa de 20% do valor restante do contrato."
ACHADO_VALIDO = {
    "tipo": "multa de rescisão",
    "valor_ou_percentual": "20%",
    "impacto": "alto",
    "trecho_original": "multa de 20% do valor restante",
}


def resposta_gemini(objeto):
    return json.dumps(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(objeto, ensure_ascii=False)}]
                    }
                }
            ]
        }
    ).encode("utf-8")


class RespostaFalsa:
    def __init__(self, conteudo):
        self.conteudo = conteudo

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.conteudo


def test_retorna_achados_validos_e_metadados(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    requisicoes = []

    def urlopen_falso(requisicao, timeout):
        requisicoes.append((requisicao, timeout))
        return RespostaFalsa(resposta_gemini({"clausulas": [ACHADO_VALIDO]}))

    monkeypatch.setattr(modulo, "urlopen", urlopen_falso)

    resultado = modulo.analisar_clausulas(TEXTO)

    assert resultado["clausulas"] == [ACHADO_VALIDO]
    assert resultado["modelo"] == modulo.MODELO_PADRAO
    assert resultado["versao_prompt"] == modulo.VERSAO_PROMPT
    assert len(requisicoes) == 1
    assert requisicoes[0][1] == modulo.TIMEOUT_SEGUNDOS

    corpo = json.loads(requisicoes[0][0].data)
    assert "systemInstruction" in corpo
    config = corpo["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"] == modulo.SCHEMA_RESPOSTA
    assert corpo["contents"][0]["parts"][0]["text"].find(TEXTO) >= 0


def test_descarta_trecho_que_nao_existe_no_texto(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    achado_inventado = {
        **ACHADO_VALIDO,
        "trecho_original": "multa de 80% do valor restante",
    }
    monkeypatch.setattr(
        modulo,
        "urlopen",
        lambda *_args, **_kwargs: RespostaFalsa(
            resposta_gemini({"clausulas": [ACHADO_VALIDO, achado_inventado]})
        ),
    )

    resultado = modulo.analisar_clausulas(TEXTO)

    assert resultado["clausulas"] == [ACHADO_VALIDO]


def test_tenta_novamente_se_o_json_da_llm_for_invalido(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    tentativas = iter(
        [
            RespostaFalsa(
                json.dumps(
                    {"candidates": [{"content": {"parts": [{"text": "não é JSON"}]}}]}
                ).encode("utf-8")
            ),
            RespostaFalsa(resposta_gemini({"clausulas": [ACHADO_VALIDO]})),
        ]
    )
    chamadas = []
    monkeypatch.setattr(modulo, "urlopen", lambda *_a, **_k: (chamadas.append(1), next(tentativas))[1])
    monkeypatch.setattr(modulo, "time", type("TempoFalso", (), {"sleep": staticmethod(lambda _s: None)}))

    resultado = modulo.analisar_clausulas(TEXTO)

    assert resultado["clausulas"] == [ACHADO_VALIDO]
    assert len(chamadas) == 2


def test_erro_claro_quando_limite_429_persiste(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    chamadas = []

    def limite_falso(*_args, **_kwargs):
        chamadas.append(1)
        raise HTTPError(
            url="https://example.invalid/gemini",
            code=429,
            msg="rate limited",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(modulo, "urlopen", limite_falso)
    monkeypatch.setattr(modulo, "_aguardar_retentativa", lambda *_args: None)

    with pytest.raises(modulo.ErroAnaliseClausulas, match="limitou as requisições"):
        modulo.analisar_clausulas(TEXTO)

    assert len(chamadas) == modulo.MAX_TENTATIVAS


def test_erro_claro_quando_timeout_persiste(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    chamadas = []

    def timeout_falso(*_args, **_kwargs):
        chamadas.append(1)
        raise TimeoutError("tempo esgotado")

    monkeypatch.setattr(modulo, "urlopen", timeout_falso)
    monkeypatch.setattr(modulo, "_aguardar_retentativa", lambda *_args: None)

    with pytest.raises(modulo.ErroAnaliseClausulas, match="falha de rede"):
        modulo.analisar_clausulas(TEXTO)

    assert len(chamadas) == modulo.MAX_TENTATIVAS


@pytest.mark.parametrize(
    "texto",
    ["", "   ", "CPF 123.456.789-00", "CNPJ 12.345.678/0001-90", "email a@b.com"],
)
def test_rejeita_texto_vazio_ou_com_padrao_de_dado_pessoal(texto, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    chamadas = []
    monkeypatch.setattr(modulo, "urlopen", lambda *_a, **_k: chamadas.append(1))

    with pytest.raises(modulo.TextoClausulasInvalido):
        modulo.analisar_clausulas(texto)

    assert chamadas == []


def test_requer_chave_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(modulo.ErroAnaliseClausulas, match="GEMINI_API_KEY"):
        modulo.analisar_clausulas(TEXTO)
