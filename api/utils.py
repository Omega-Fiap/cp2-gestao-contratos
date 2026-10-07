from datetime import datetime, timezone
from decimal import Decimal

from api.exceptions import ErroAplicacao


def agora():
    """Data/hora atual em UTC, sem fuso (formato já usado nas colunas)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(valor):
    return valor.isoformat() if valor is not None else None


def numero_decimal(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def texto(valor):
    """Devolve a string sem espaços sobrando, ou None se vazia."""
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def parse_date(valor):
    if valor in (None, ""):
        return None
    return datetime.strptime(valor, "%Y-%m-%d").date()


def data_ou_erro(valor):
    try:
        return parse_date(valor)
    except (ValueError, TypeError):
        raise ErroAplicacao("Datas devem usar o formato YYYY-MM-DD.")


def parse_datetime(valor):
    if valor in (None, ""):
        return None

    # Aceita: 2026-09-07T18:30:00 ou 2026-09-07 18:30:00
    valor = valor.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")


def datahora_ou_erro(valor):
    try:
        return parse_datetime(valor)
    except (ValueError, TypeError, AttributeError):
        raise ErroAplicacao("Use uma data/hora ISO, por exemplo 2026-09-07T18:30:00.")
