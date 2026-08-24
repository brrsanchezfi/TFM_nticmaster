"""Simulador del sistema origen: emite eventos CDC sobre clientes.

En un entorno con Azure SQL, estos eventos los produciría Change Tracking al
capturar los INSERT/UPDATE/DELETE de la base operacional. Aquí los genera este
módulo, que emite exactamente el mismo contrato de datos: una fila por evento
con `op_type` (I/U/D) y `op_ts`.

Lo que el TFM demuestra es el tratamiento de ese feed —deduplicar por clave,
aplicar el último evento y marcar las bajas sin borrarlas—, y ese tratamiento
es idéntico venga el evento de Change Tracking, de Debezium o de un fichero.

Sin Spark: listas de diccionarios, testeables sin sesión.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

SEGMENTOS = ["retail", "premium", "corporativo"]
CIUDADES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao"]
DOMINIOS = ["example.com", "correo.es", "mail.net"]


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cliente(rnd: random.Random, numero: int) -> dict:
    nombre = f"Cliente {numero:04d}"
    return {
        "cliente_id": f"CLI-{numero:05d}",
        "nombre": nombre,
        "email": f"cliente{numero:04d}@{rnd.choice(DOMINIOS)}",
        "ciudad": rnd.choice(CIUDADES),
        "segmento": rnd.choice(SEGMENTOS),
        "fecha_alta": (date.today() - timedelta(days=rnd.randint(0, 720))).isoformat(),
    }


def carga_inicial(rows: int, semilla: int | None = 42) -> list[dict]:
    """Alta de la cartera inicial: todos los eventos son I."""
    rnd = random.Random(semilla)
    momento = _ahora()
    return [
        {**_cliente(rnd, i), "op_type": "I", "op_ts": momento}
        for i in range(1, rows + 1)
    ]


def lote_cambios(
    clientes_vigentes: list[dict],
    semilla: int | None = 7,
    n_altas: int = 10,
    n_updates: int = 25,
    n_bajas: int = 5,
) -> list[dict]:
    """Emite un lote de eventos sobre la cartera existente.

    Los eventos van mezclados en una sola lista, como saldrían de un feed real:
    es la promoción a Silver quien decide qué hacer con cada uno.
    """
    rnd = random.Random(semilla)
    momento = _ahora()
    eventos: list[dict] = []

    # Altas: identificadores por encima del máximo actual, para no colisionar.
    ultimo = max(
        (int(c["cliente_id"].split("-")[1]) for c in clientes_vigentes),
        default=0,
    )
    for i in range(ultimo + 1, ultimo + 1 + n_altas):
        eventos.append({**_cliente(rnd, i), "op_type": "I", "op_ts": momento})

    disponibles = list(clientes_vigentes)
    rnd.shuffle(disponibles)

    # Modificaciones: cambia lo que cambia en la vida real de un cliente.
    for cliente in disponibles[:n_updates]:
        modificado = dict(cliente)
        campo = rnd.choice(["email", "ciudad", "segmento"])
        if campo == "email":
            numero = cliente["cliente_id"].split("-")[1]
            modificado["email"] = f"cliente{int(numero):04d}@{rnd.choice(DOMINIOS)}"
        else:
            modificado[campo] = rnd.choice(
                CIUDADES if campo == "ciudad" else SEGMENTOS
            )
        eventos.append({**modificado, "op_type": "U", "op_ts": momento})

    # Bajas: sobre clientes que no se están modificando en este mismo lote, para
    # que el resultado no dependa del orden de aplicación.
    tocados = {e["cliente_id"] for e in eventos}
    candidatos = [c for c in disponibles if c["cliente_id"] not in tocados]
    for cliente in candidatos[:n_bajas]:
        eventos.append({
            **cliente,
            "op_type": "D",
            "op_ts": momento,
        })

    rnd.shuffle(eventos)
    return eventos
