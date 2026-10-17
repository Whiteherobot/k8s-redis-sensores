"""Sensor de un robot de almacén: publica una lectura en Redis cada INTERVALO segundos.

Cada réplica toma su id del nombre del pod (SENSOR_ID), así con 3 réplicas hay
3 sensores distintos. Si Redis no está, reintenta con espera creciente en vez
de terminar.
"""
import json
import os
import random
import time
from datetime import datetime, timezone

import redis

LISTA = "sensor:data"
ULTIMOS = "sensor:latest"
MAX_REGISTROS = 1000


def lectura(sensor_id: str, anterior: float | None, rng: random.Random) -> dict:
    """Temperatura del motor en °C: varía de a poco respecto de la anterior."""
    base = anterior if anterior is not None else rng.uniform(35, 45)
    valor = min(max(base + rng.uniform(-1.5, 1.5), 20.0), 90.0)
    return {
        "sensor_id": sensor_id,
        "valor": round(valor, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def publicar(r: redis.Redis, dato: dict) -> None:
    """Agrega la lectura al historial (acotado) y actualiza la última del sensor, en una transacción."""
    texto = json.dumps(dato)
    with r.pipeline(transaction=True) as p:
        p.lpush(LISTA, texto)
        p.ltrim(LISTA, 0, MAX_REGISTROS - 1)
        p.hset(ULTIMOS, dato["sensor_id"], texto)
        p.execute()


def main() -> None:
    sensor_id = os.getenv("SENSOR_ID", "rbt-01")
    intervalo = float(os.getenv("INTERVALO", "3"))
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis-service"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    rng = random.Random()
    anterior = None
    espera = 1.0
    print(f"sensor {sensor_id} publicando cada {intervalo} s", flush=True)
    while True:
        try:
            dato = lectura(sensor_id, anterior, rng)
            publicar(r, dato)
            anterior = dato["valor"]
            espera = 1.0
            time.sleep(intervalo)
        except redis.exceptions.AuthenticationError:
            raise  # con la clave mal no tiene sentido reintentar
        except redis.exceptions.RedisError as e:
            print(f"Redis no responde ({e}); reintento en {espera:.0f} s", flush=True)
            time.sleep(espera)
            espera = min(espera * 2, 30)


if __name__ == "__main__":
    main()
