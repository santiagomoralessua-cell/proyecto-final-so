import os
import random
import socket
import time

from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
app.json.ensure_ascii = False  # para que "esperó_ms" salga con tilde

# El nombre lo inyectamos desde docker-compose (variable de entorno SERVER_NAME)
SERVER_NAME = os.getenv("SERVER_NAME", "sin-nombre")

# Expone /metrics con las métricas flask_http_request_* (tasa y latencia).
# La etiqueta "server" permite separar en Grafana a server 1, 2 y 3.
metrics = PrometheusMetrics(app, default_labels={"server": SERVER_NAME})
metrics.info("backend_info", "Información del backend", server=SERVER_NAME)


@app.route("/")
def index():
    return (
        f"<h1>Hello from {SERVER_NAME}</h1>\n"
        f"<p>Contenedor: {socket.gethostname()}</p>\n"
    )


@app.route("/health")
@metrics.do_not_track()
def health():
    return jsonify(status="ok", server=SERVER_NAME)


@app.route("/headers")
def headers():
    # Muestra qué cabeceras recibe realmente el backend (útil para ver X-Forwarded-For)
    return jsonify(
        server=SERVER_NAME,
        ip_que_ve_flask=request.remote_addr,
        cabeceras=dict(request.headers),
    )


@app.route("/slow")
def slow():
    # Simula trabajo pesado: /slow?ms=500 tarda 500 ms en responder.
    # Sin ?ms= tarda un valor aleatorio entre 10 y 200 ms (lo usa la prueba de carga)
    if "ms" in request.args:
        ms = min(int(request.args["ms"]), 30000)
    else:
        ms = random.randint(10, 200)
    time.sleep(ms / 1000)
    return jsonify(server=SERVER_NAME, esperó_ms=ms)


@app.route("/error")
def error():
    # Falla el 20 % de las veces, para ver errores 5xx en Grafana
    if random.random() < 0.2:
        return jsonify(server=SERVER_NAME, error="fallo simulado"), 500
    return jsonify(server=SERVER_NAME, ok=True)


@app.after_request
def marcar_backend(resp):
    resp.headers["X-Backend"] = SERVER_NAME
    return resp
