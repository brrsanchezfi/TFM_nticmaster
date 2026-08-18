"""Generador de pedidos y de lotes de cambios para el caso CDF.

Produce dos cosas:

- una carga inicial de pedidos, para sembrar la tabla origen;
- lotes de cambios (INSERT / UPDATE / DELETE) que se aplican sobre ella, que
  es lo que hace que el Change Data Feed tenga algo que reportar.

Sin funciones de Spark: son listas de diccionarios, para poder testearlas sin
levantar una sesión.
"""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

ESTADOS = ["nuevo", "pagado", "enviado", "entregado", "cancelado"]

# Un pedido solo avanza hacia adelante, o se cancela. Refleja un ciclo de vida
# realista y hace que los UPDATE muevan pedidos entre grupos del agregado,
# que es justo lo que el caso quiere demostrar.
TRANSICIONES = {
    "nuevo": ["pagado", "cancelado"],
    "pagado": ["enviado", "cancelado"],
    "enviado": ["entregado"],
    "entregado": [],
    "cancelado": [],
}

CIUDADES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao"]


def generar_pedidos(rows: int, semilla: int | None = 42) -> list[dict]:
    """Carga inicial: todos los pedidos nacen en estado 'nuevo'."""
    rnd = random.Random(semilla)
    hoy = date.today()

    return [
        {
            "pedido_id": str(uuid.UUID(int=rnd.getrandbits(128))),
            "cliente_id": f"CLI-{rnd.randint(1, 200):04d}",
            "fecha": (hoy - timedelta(days=rnd.randint(0, 14))).isoformat(),
            "estado": "nuevo",
            "ciudad": rnd.choice(CIUDADES),
            "unidades": rnd.randint(1, 6),
            "importe": round(rnd.uniform(15.0, 890.0), 2),
        }
        for _ in range(rows)
    ]


def generar_lote_cambios(
    pedidos_actuales: list[dict],
    semilla: int | None = 7,
    n_altas: int = 20,
    n_updates: int = 30,
    n_bajas: int = 10,
) -> dict[str, list]:
    """Genera un lote con las tres operaciones sobre los pedidos existentes.

    Devuelve
    --------
    dict con las claves ``altas`` (filas nuevas), ``updates`` (filas con el
    estado avanzado) y ``bajas`` (lista de pedido_id a borrar).
    """
    rnd = random.Random(semilla)
    hoy = date.today()

    altas = [
        {
            "pedido_id": str(uuid.UUID(int=rnd.getrandbits(128))),
            "cliente_id": f"CLI-{rnd.randint(1, 200):04d}",
            "fecha": hoy.isoformat(),
            "estado": "nuevo",
            "ciudad": rnd.choice(CIUDADES),
            "unidades": rnd.randint(1, 6),
            "importe": round(rnd.uniform(15.0, 890.0), 2),
        }
        for _ in range(n_altas)
    ]

    # Solo se pueden actualizar pedidos cuyo estado admita transición.
    candidatos = [p for p in pedidos_actuales if TRANSICIONES.get(p["estado"])]
    rnd.shuffle(candidatos)
    updates = []
    for pedido in candidatos[:n_updates]:
        avanzado = dict(pedido)
        avanzado["estado"] = rnd.choice(TRANSICIONES[pedido["estado"]])
        updates.append(avanzado)

    # Las bajas se eligen entre pedidos que no se están actualizando en este
    # mismo lote, para que no haya un UPDATE y un DELETE de la misma fila.
    tocados = {p["pedido_id"] for p in updates}
    borrables = [p["pedido_id"] for p in pedidos_actuales if p["pedido_id"] not in tocados]
    rnd.shuffle(borrables)
    bajas = borrables[:n_bajas]

    return {"altas": altas, "updates": updates, "bajas": bajas}
