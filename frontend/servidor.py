"""
Backend do sistema (front-end + ponte para a API).

- Serve as páginas da pasta `frontend/`.
- Encaminha tudo que chega em /api/... para a API externa definida em API_URL,
  então o navegador só conversa com este servidor (sem problemas de CORS).

Rodar:  python -m frontend.servidor
"""
import os

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000").rstrip("/")
PORTA = int(os.getenv("PORT", "8000"))
PASTA_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

app = Flask(__name__, static_folder=PASTA_FRONTEND, static_url_path="")


# ============================================================
# PONTE PARA A API
# ============================================================

@app.route("/api/<path:rota>", methods=["GET", "POST", "PUT", "DELETE"])
def encaminhar(rota):
    # Só repassa o necessário: tipo do conteúdo e o token de login.
    cabecalhos = {}
    for nome in ("Content-Type", "Authorization"):
        if nome in request.headers:
            cabecalhos[nome] = request.headers[nome]

    try:
        resposta = requests.request(
            request.method,
            f"{API_URL}/{rota}",
            params=request.args,
            data=request.get_data(),
            headers=cabecalhos,
            timeout=15,
        )
    except requests.exceptions.RequestException:
        return jsonify({"erro": f"Não foi possível conectar à API em {API_URL}."}), 502

    return Response(
        resposta.content,
        status=resposta.status_code,
        content_type=resposta.headers.get("Content-Type", "application/json"),
    )


# ============================================================
# PÁGINAS
# ============================================================

@app.get("/")
def inicio():
    return send_from_directory(PASTA_FRONTEND, "index.html")


@app.errorhandler(404)
def nao_encontrado(_):
    if request.path.startswith("/api/"):
        return jsonify({"erro": "Rota não encontrada."}), 404
    return send_from_directory(PASTA_FRONTEND, "index.html"), 404


if __name__ == "__main__":
    print(f"Sistema:  http://127.0.0.1:{PORTA}")
    print(f"API em:   {API_URL}")
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=PORTA,
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
