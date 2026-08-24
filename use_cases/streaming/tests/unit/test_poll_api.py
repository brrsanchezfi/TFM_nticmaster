"""Tests del productor — sin red: la respuesta de la API se simula."""
import json
from unittest.mock import patch

from weather_events.producer import poll_api

RESPUESTA = {
    "latitude": 40.4,
    "longitude": -3.7,
    "current": {
        "time": "2026-08-18T10:00",
        "temperature_2m": 24.5,
        "relative_humidity_2m": 42,
        "wind_speed_10m": 13.2,
        "weather_code": 3,
    },
}


class _RespuestaFalsa:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_normaliza_la_respuesta_de_la_api():
    with patch.object(poll_api.urllib.request, "urlopen",
                      return_value=_RespuestaFalsa(RESPUESTA)):
        lectura = poll_api.consultar_ciudad("Madrid", 40.4, -3.7)

    assert lectura["ciudad"] == "Madrid"
    assert lectura["hora"] == "2026-08-18T10:00"
    assert lectura["temperatura"] == 24.5
    assert lectura["humedad"] == 42
    assert lectura["codigo_tiempo"] == 3
    assert lectura["capturado_at"]


def test_capturado_at_es_distinto_de_la_hora_de_observacion():
    """La API devuelve la última observación publicada, que puede ser de hace
    rato: por eso se guardan las dos marcas temporales."""
    with patch.object(poll_api.urllib.request, "urlopen",
                      return_value=_RespuestaFalsa(RESPUESTA)):
        lectura = poll_api.consultar_ciudad("Madrid", 40.4, -3.7)

    assert lectura["capturado_at"] != lectura["hora"]


def test_una_ciudad_caida_no_tumba_el_lote():
    """Perder una lectura no justifica descartar las demás: la siguiente
    pasada la recupera."""
    def falla_solo_madrid(ciudad, lat, lon):
        if ciudad == "Madrid":
            raise TimeoutError("la API no responde")
        return {"ciudad": ciudad}

    with patch.object(poll_api, "consultar_ciudad", side_effect=falla_solo_madrid):
        lecturas = poll_api.recolectar({
            "Madrid": (40.4, -3.7),
            "Bilbao": (43.2, -2.9),
        })

    assert [l["ciudad"] for l in lecturas] == ["Bilbao"]


def test_valores_ausentes_no_rompen_la_normalizacion():
    incompleta = {"latitude": 40.4, "longitude": -3.7, "current": {"time": "2026-08-18T10:00"}}

    with patch.object(poll_api.urllib.request, "urlopen",
                      return_value=_RespuestaFalsa(incompleta)):
        lectura = poll_api.consultar_ciudad("Madrid", 40.4, -3.7)

    assert lectura["temperatura"] is None
    assert lectura["humedad"] is None
