"""Entrypoint del Databricks Job: propaga a Gold solo lo que cambió.

Es el núcleo del caso de uso. En lugar de reconstruir el agregado leyendo la
tabla de pedidos entera, pregunta al Change Data Feed qué versiones nuevas hay
desde la última ejecución, deduce qué estados quedaron desactualizados y
recalcula únicamente esos.
"""
from __future__ import annotations

from DKOps.table_governance import TableReader, TableWriter
from orders.pipeline import build_context, contratos, parse_args
from orders.transformations.cdf_metrics import (
    estados_afectados,
    estados_vaciados,
    recalcular_agregado,
)
from pyspark.sql import functions as F


def _version_actual(spark, tabla: str) -> int:
    """Última versión de Delta de la tabla origen."""
    fila = spark.sql(f"DESCRIBE HISTORY {tabla} LIMIT 1").select("version").collect()[0]
    return int(fila["version"])


def _ultima_procesada(spark, control: str, dataset: str) -> int | None:
    """Puntero guardado, o None si es la primera vez que se procesa."""
    if not spark.catalog.tableExists(control):
        return None
    filas = (
        spark.table(control)
        .where(F.col("dataset") == dataset)
        .select("ultima_version")
        .collect()
    )
    return int(filas[0]["ultima_version"]) if filas else None


def _carga_inicial(spark, origen, agregado) -> None:
    """Construye el agregado completo la primera vez.

    El Change Data Feed sirve para propagar cambios *a partir de* un estado
    conocido, no para construirlo. Además, leer el feed desde la versión 0
    cruza la creación de la tabla y Delta lo rechaza con
    ``DELTA_CHANGE_DATA_FEED_INCOMPATIBLE_DATA_SCHEMA``, porque el rango
    atraviesa un cambio de esquema.

    Así que el arranque en frío es un cálculo completo, y a partir de ahí todo
    es incremental.
    """
    pedidos = spark.table(origen.full_name)
    estados = [f["estado"] for f in pedidos.select("estado").distinct().collect()]
    TableWriter(agregado).overwrite(recalcular_agregado(pedidos, estados))
    print(f"Carga inicial del agregado | estados={sorted(estados)}")


def main() -> None:
    args = parse_args()
    launcher, root = build_context(args.config, args.bundle_root, proceso="propagate_cdf")
    spark = launcher.spark
    cts = contratos(root, launcher.env)

    origen, agregado, control = cts["origen"], cts["agregado"], cts["control"]
    tabla_origen = origen.full_name

    version_actual = _version_actual(spark, tabla_origen)
    ultima = _ultima_procesada(spark, control.full_name, tabla_origen)

    if ultima is None:
        _carga_inicial(spark, origen, agregado)
        filas_cambio = 0

    elif ultima >= version_actual:
        print(f"Sin cambios que propagar | version={version_actual}")
        return

    else:
        # Se arranca justo en la versión siguiente a la ya procesada, para no
        # reprocesar cambios ya propagados.
        desde = ultima + 1
        cambios = TableReader(origen).read_cdf(
            starting_version=desde, ending_version=version_actual
        )

        filas_cambio = cambios.count()
        estados = estados_afectados(cambios)
        print(
            f"CDF v{desde}..v{version_actual} | filas_cambio={filas_cambio} | "
            f"estados afectados={estados}"
        )

        if estados:
            pedidos = spark.table(tabla_origen)
            nuevo = recalcular_agregado(pedidos, estados)

            TableWriter(agregado).upsert(nuevo, keys=["estado"])

            # Un estado puede quedarse sin pedidos: el MERGE no lo tocaría y su
            # fila se quedaría con el valor viejo para siempre.
            vaciados = estados_vaciados(nuevo, estados)
            if vaciados:
                lista = ", ".join(f"'{e}'" for e in vaciados)
                TableWriter(agregado).delete(f"estado IN ({lista})")
                print(f"Estados vaciados y eliminados de Gold: {vaciados}")

    # El puntero avanza aunque no hubiera estados afectados: las versiones
    # ya se han leído y no hay que volver a mirarlas.
    puntero = spark.createDataFrame(
        [(tabla_origen, version_actual, filas_cambio)],
        "dataset string, ultima_version long, filas_procesadas long",
    ).withColumn("_actualizado_at", F.current_timestamp())

    TableWriter(control).upsert(puntero, keys=["dataset"])
    print(f"Puntero actualizado a la version {version_actual}")


if __name__ == "__main__":
    main()
