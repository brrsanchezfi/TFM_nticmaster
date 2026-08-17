"""Generador de ventas retail sintéticas para la landing zone.

El TFM no puede usar datos de empresa, así que el origen del caso batch es un
dataset generado con Faker. Escribe JSON Lines, un fichero por ejecución, en
``<landing>/ventas/``.

Uso local (escribe en disco):

    python -m retail_sales.generators.generate_sales --out /tmp/ventas --rows 500

Uso en Databricks (escribe en ADLS a través de dbutils/Spark):

    python -m retail_sales.generators.generate_sales --config config/config.dev.json
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

CATEGORIAS = {
    "Electrónica": (89.0, 1299.0),
    "Hogar": (12.0, 349.0),
    "Alimentación": (1.2, 24.0),
    "Textil": (9.9, 129.0),
    "Deporte": (14.0, 499.0),
}

CANALES = ["online", "tienda"]

CIUDADES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao", "Zaragoza"]


def generar_ventas(
    rows: int,
    dias: int = 30,
    semilla: int | None = 42,
    duplicados: float = 0.05,
) -> list[dict]:
    """Genera líneas de venta sintéticas.

    Parámetros
    ----------
    rows       : número de ventas distintas a generar.
    dias       : ventana temporal hacia atrás desde hoy.
    semilla    : fija la aleatoriedad para que el dataset sea reproducible.
    duplicados : fracción de ventas que se repiten con importe corregido.
                 Existen a propósito: sin duplicados, la estrategia
                 ``full_merge`` de Silver no demostraría nada.
    """
    rnd = random.Random(semilla)
    hoy = date.today()
    ventas: list[dict] = []

    for _ in range(rows):
        categoria = rnd.choice(list(CATEGORIAS))
        precio_min, precio_max = CATEGORIAS[categoria]
        precio = round(rnd.uniform(precio_min, precio_max), 2)
        cantidad = rnd.randint(1, 5)

        ventas.append({
            "venta_id": str(uuid.UUID(int=rnd.getrandbits(128))),
            "fecha": (hoy - timedelta(days=rnd.randint(0, dias - 1))).isoformat(),
            "cliente_id": f"CLI-{rnd.randint(1, 500):04d}",
            "producto_id": f"PRD-{rnd.randint(1, 200):04d}",
            "producto": f"{categoria} modelo {rnd.randint(1, 99)}",
            "categoria": categoria,
            "canal": rnd.choice(CANALES),
            "ciudad": rnd.choice(CIUDADES),
            "cantidad": cantidad,
            "precio_unitario": precio,
            "importe": round(cantidad * precio, 2),
        })

    # Reemisiones: la misma venta_id vuelve a llegar con el importe corregido.
    # Silver debe quedarse con la última, no con las dos.
    for venta in rnd.sample(ventas, k=int(rows * duplicados)):
        correccion = dict(venta)
        nuevo_precio = round(venta["precio_unitario"] * rnd.uniform(0.9, 1.1), 2)
        correccion["precio_unitario"] = nuevo_precio
        correccion["importe"] = round(venta["cantidad"] * nuevo_precio, 2)
        ventas.append(correccion)

    rnd.shuffle(ventas)
    return ventas


def escribir_jsonl(ventas: list[dict], destino: Path) -> Path:
    """Escribe las ventas como JSON Lines en un fichero con marca temporal."""
    destino.mkdir(parents=True, exist_ok=True)
    fichero = destino / f"ventas_{date.today().isoformat()}_{uuid.uuid4().hex[:8]}.json"
    with open(fichero, "w", encoding="utf-8") as f:
        for venta in ventas:
            f.write(json.dumps(venta, ensure_ascii=False) + "\n")
    return fichero


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="/tmp/retail_sales/landing/ventas",
                        help="Directorio destino de los ficheros JSON.")
    parser.add_argument("--rows", type=int, default=500,
                        help="Número de ventas distintas a generar.")
    parser.add_argument("--dias", type=int, default=30,
                        help="Ventana temporal hacia atrás.")
    parser.add_argument("--semilla", type=int, default=42,
                        help="Semilla; usar valores distintos para lotes distintos.")
    args = parser.parse_args()

    ventas = generar_ventas(args.rows, dias=args.dias, semilla=args.semilla)
    fichero = escribir_jsonl(ventas, Path(args.out))
    print(f"{len(ventas)} filas escritas en {fichero}")


if __name__ == "__main__":
    main()
