import os

# Deve rodar antes de importar api.app: os testes nunca podem tocar o banco real.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "chave-de-teste")
