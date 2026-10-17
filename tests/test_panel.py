import json

import fakeredis
import pytest
import redis

from app import crear_app


@pytest.fixture
def r():
    r = fakeredis.FakeRedis(decode_responses=True)
    for i, (s, v) in enumerate([("s-b", 41.0), ("s-a", 72.5), ("s-b", 42.25)]):
        dato = json.dumps({"sensor_id": s, "valor": v, "timestamp": f"2026-10-17T10:00:0{i}+00:00"})
        r.lpush("sensor:data", dato)
        r.hset("sensor:latest", s, dato)
    return r


def test_api_con_ultimo_valor_por_sensor_e_historial(r):
    datos = crear_app(r).test_client().get("/api/lecturas").get_json()
    assert [(s["sensor_id"], s["valor"]) for s in datos["sensores"]] == [("s-a", 72.5), ("s-b", 42.25)]
    assert [h["valor"] for h in datos["historial"]] == [42.25, 72.5, 41.0]
    assert datos["total"] == 3


def test_pagina_con_alerta_de_temperatura_alta_y_datos_escapados(r):
    r.hset("sensor:latest", "<script>x</script>", json.dumps({"sensor_id": "<script>x</script>", "valor": 30, "timestamp": "2026-10-17T10:00:00+00:00"}))
    html = crear_app(r).test_client().get("/").get_data(as_text=True)
    assert 'class="valor alto">72.5 °C' in html
    assert "2026-10-17 10:00:02" in html
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_sin_redis_avisa_y_no_esta_listo():
    caido = redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2)
    cliente = crear_app(caido).test_client()
    pagina = cliente.get("/")
    assert pagina.status_code == 503
    assert "No hay conexión con Redis" in pagina.get_data(as_text=True)
    assert cliente.get("/salud").status_code == 503
    assert cliente.get("/api/lecturas").status_code == 503
