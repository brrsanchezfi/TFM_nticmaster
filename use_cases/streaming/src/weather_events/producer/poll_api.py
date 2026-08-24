"""Productor de eventos: consulta una API meteorológica pública.

El TFM evita levantar Kafka o Event Hubs, que serían infraestructura de pago.
En su lugar, un job corto consulta Open-Meteo —gratuita y sin autenticación— y
deja un fichero JSON en la landing zone. Auto Loader se encarga del resto.

El patrón es el mismo que con una cola real: alguien deposita eventos, otro los
consume de forma incremental. Lo que cambia es el transporte.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.open-meteo.com/v1/forecast"

# Coordenadas fijas: la gracia está en la evolución temporal de cada ciudad,
# no en qué ciudades se consultan.
CIUDADES = {
    "Madrid": (40.4168, -3.7038),
    "Barcelona": (41.3874, 2.1686),
    "Valencia": (39.4699, -0.3763),
    "Sevilla": (37.3891, -5.9845),
    "Bilbao": (43.2630, -2.9350),
}

CAMPOS = "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"

TIMEOUT = 20


def consultar_ciudad(ciudad: str, lat: float, lon: float) -> dict:
    """Consulta la observación actual de una ciudad y la normaliza."""
    url = (
        f"{API_URL}?latitude={lat}&longitude={lon}"
        f"&current={CAMPOS}&timezone=UTC"
    )
    with urllib.request.urlopen(url, timeout=TIMEOUT) as respuesta:
        datos = json.loads(respuesta.read())

    actual = datos.get("current", {})
    return {
        "ciudad": ciudad,
        "latitud": float(datos.get("latitude", lat)),
        "longitud": float(datos.get("longitude", lon)),
        # 'hora' es la marca de la observación, que la API mantiene hasta
        # publicar una nueva. Es lo que permite deduplicar en Silver.
        "hora": actual.get("time"),
        "temperatura": _num(actual.get("temperature_2m")),
        "humedad": _int(actual.get("relative_humidity_2m")),
        "viento": _num(actual.get("wind_speed_10m")),
        "codigo_tiempo": _int(actual.get("weather_code")),
        "capturado_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _num(valor) -> float | None:
    return float(valor) if valor is not None else None


def _int(valor) -> int | None:
    return int(valor) if valor is not None else None


def recolectar(ciudades: dict[str, tuple[float, float]] | None = None) -> list[dict]:
    """Consulta todas las ciudades y devuelve las lecturas obtenidas.

    Si una ciudad falla, se registra y se continúa: perder una lectura no
    justifica tirar el lote entero, y la siguiente pasada la recuperará.
    """
    objetivo = ciudades or CIUDADES
    lecturas = []

    for ciudad, (lat, lon) in objetivo.items():
        try:
            lecturas.append(consultar_ciudad(ciudad, lat, lon))
        except Exception as exc:
            print(f"[{ciudad}] fallo al consultar la API: {exc}")

    return lecturas
