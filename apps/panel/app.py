"""Panel de solo lectura con la última lectura de cada sensor y el historial reciente."""
import json
import os

import redis
from flask import Flask, jsonify, render_template

LISTA = "sensor:data"
ULTIMOS = "sensor:latest"


def crear_app(r: redis.Redis | None = None, limite: int = 50) -> Flask:
    app = Flask(__name__)
    r = r or redis.Redis(
        host=os.getenv("REDIS_HOST", "redis-service"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
        socket_timeout=3,
        socket_connect_timeout=3,
    )

    def datos():
        ultimos = sorted((json.loads(v) for v in r.hgetall(ULTIMOS).values()), key=lambda d: d["sensor_id"])
        historial = [json.loads(x) for x in r.lrange(LISTA, 0, limite - 1)]
        return {"sensores": ultimos, "historial": historial, "total": r.llen(LISTA)}

    @app.get("/")
    def inicio():
        try:
            return render_template("index.html", **datos(), error=None)
        except redis.exceptions.RedisError:
            return render_template("index.html", sensores=[], historial=[], total=0,
                                   error="No hay conexión con Redis; reintentando."), 503

    @app.get("/api/lecturas")
    def lecturas():
        try:
            return jsonify(datos())
        except redis.exceptions.RedisError:
            return jsonify(error="Redis no disponible"), 503

    @app.get("/salud")
    def salud():
        try:
            r.ping()
            return jsonify(estado="ok")
        except redis.exceptions.RedisError:
            return jsonify(estado="sin-redis"), 503

    return app


if __name__ == "__main__":
    crear_app().run(host="0.0.0.0", port=8080)
