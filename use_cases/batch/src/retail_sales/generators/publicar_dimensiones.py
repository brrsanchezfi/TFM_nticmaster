"""Publica los catálogos en la landing zone, como haría un sistema maestro.

**Esto no forma parte del pipeline.** Es el sustituto de un origen que en un
entorno real no habría que escribir: un maestro de productos, un CRM o un ERP
dejarían los ficheros en la landing por su cuenta, y el pipeline empezaría a
partir de ahí.

Vive aquí, junto al generador de ventas, y no en ``jobs/``, precisamente para
que la separación quede clara: ``jobs/`` es lo que se despliega como pipeline;
``generators/`` es el atrezo que simula los sistemas de origen.
"""
from __future__ import annotations

import json

from retail_sales.generators.dimensiones import DIMENSIONES

ANCHO = 72


def _banner(titulo: str, lineas: list[str]) -> None:
    print("=" * ANCHO)
    print(f"  {titulo}")
    for l in lineas:
        print(f"  {l}")
    print("=" * ANCHO)


def publicar(spark, env) -> int:
    """Deja cada catálogo como JSON Lines en la landing. Devuelve las filas."""
    _banner(
        "SIMULACIÓN DEL ORIGEN — datos de prueba, esto NO es ingesta",
        [
            "",
            "Publica los catálogos en la landing zone como lo haría un",
            "sistema maestro (un ERP, un CRM, un PIM).",
            "",
            "En un entorno real este bloque NO EXISTE: los ficheros los",
            "deja el origen y el pipeline arranca en la ingesta a Bronze.",
        ],
    )

    total = 0
    for nombre, (filas, columnas) in DIMENSIONES.items():
        # JSON Lines: un objeto por línea, que es lo que espera el contrato de
        # ingesta (`format: json`, `multiLine: false`).
        lineas = [
            (json.dumps(dict(zip(columnas, fila)), ensure_ascii=False),)
            for fila in filas
        ]
        destino = f"{env.get_path('landing')}/{nombre}"

        # coalesce(1) y overwrite: el catálogo es diminuto y la landing debe
        # quedar con un solo fichero por dimensión, el vigente. El maestro
        # publica el estado actual, no su historia.
        (
            spark.createDataFrame(lineas, "linea string")
            .coalesce(1)
            .write.mode("overwrite").text(destino)
        )

        total += len(filas)
        print(f"  [dummy] {nombre:<16} {len(filas):>3} filas → {destino}")

    _banner(
        "FIN DE LA SIMULACIÓN — a partir de aquí, el pipeline de verdad",
        [f"{total} filas publicadas en {len(DIMENSIONES)} catálogos."],
    )
    return total
