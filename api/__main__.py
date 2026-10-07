"""Executa a API: python -m api"""
import os

from api import create_app
from api.extensions import db

app = create_app()

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
