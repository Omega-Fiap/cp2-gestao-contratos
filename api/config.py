import os

from dotenv import load_dotenv

load_dotenv()


def _uri_do_banco():
    # DATABASE_URL (ex.: "sqlite://" nos testes) tem prioridade sobre as variáveis DB_*.
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT"),
        os.getenv("DB_NAME"),
    )


class Config:
    SQLALCHEMY_DATABASE_URI = _uri_do_banco()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Defina SECRET_KEY no .env em produção.
    SECRET_KEY = os.getenv("SECRET_KEY") or "chave-apenas-para-desenvolvimento"
    TOKEN_VALIDADE_SEGUNDOS = 60 * 60 * 8  # 8 horas
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
