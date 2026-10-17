import json
import random

import fakeredis

from sensor import MAX_REGISTROS, lectura, publicar


def test_la_lectura_cambia_de_a_poco_y_queda_en_rango():
    rng = random.Random(1)
    anterior = None
    for _ in range(500):
        dato = lectura("rbt-01", anterior, rng)
        assert 20 <= dato["valor"] <= 90
        if anterior is not None:
            assert abs(dato["valor"] - anterior) <= 1.5 + 1e-9
        anterior = dato["valor"]
    assert dato["sensor_id"] == "rbt-01"
    assert dato["timestamp"].endswith("+00:00")


def test_publica_historial_acotado_y_ultima_lectura_por_sensor():
    r = fakeredis.FakeRedis(decode_responses=True)
    for i in range(MAX_REGISTROS + 20):
        publicar(r, {"sensor_id": f"s{i % 3}", "valor": float(i), "timestamp": "t"})
    assert r.llen("sensor:data") == MAX_REGISTROS
    assert json.loads(r.lindex("sensor:data", 0))["valor"] == MAX_REGISTROS + 19
    assert sorted(r.hkeys("sensor:latest")) == ["s0", "s1", "s2"]
    assert json.loads(r.hget("sensor:latest", "s2"))["valor"] == MAX_REGISTROS + 19
