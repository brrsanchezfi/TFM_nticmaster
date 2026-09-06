"""Entrypoint del Databricks Job: deja un lote de eventos en la landing zone.

Es el equivalente al productor de una cola. Consulta la API, escribe un fichero
JSON y termina. Auto Loader lo recogerá en la tarea siguiente.
"""
from __future__ import annotations

from datetime import datetime, timezone

from weather_events.pipeline import build_engine, parse_args
from weather_events.producer.poll_api import recolectar


def main() -> None:
    args = parse_args()
    launcher, _ = build_engine(args.config, args.bundle_root, proceso="poll_api")
    spark, env = launcher.spark, launcher.env

    lecturas = recolectar()
    if not lecturas:
        raise RuntimeError("La API no devolvió ninguna lectura")

    destino = f"{env.get_path('landing')}/eventos"
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    # coalesce(1): un fichero por ejecución en lugar de una partición por
    # núcleo. Con cinco lecturas, repartirlas no aporta nada y ensucia la
    # landing con ficheros vacíos.
    (
        spark.createDataFrame(lecturas)
        .coalesce(1)
        .write.mode("append")
        .json(f"{destino}/lote={marca}")
    )

    print(f"{len(lecturas)} lecturas escritas en {destino}/lote={marca}")


if __name__ == "__main__":
    main()
