"""Entrypoint del Databricks Job: aplica cambios sobre la tabla origen.

Este job es el que da trabajo al Change Data Feed. En un sistema real su
equivalente sería la aplicación operacional que mantiene los pedidos; aquí lo
simula un generador para que la PoC sea reproducible.

La primera ejecución siembra la tabla; las siguientes aplican un lote de
INSERT, UPDATE y DELETE.
"""
from __future__ import annotations

from DKOps.table_governance import TableWriter
from orders.generators.generate_orders import generar_lote_cambios, generar_pedidos
from orders.pipeline import build_context, contratos, parse_args
from pyspark.sql import functions as F

PEDIDOS_INICIALES = 300


def _existe(spark, tabla: str) -> bool:
    return spark.catalog.tableExists(tabla)


def _semilla(spark, tabla: str, lote: int) -> int:
    """Resuelve la semilla del lote.

    Con ``--lote 0`` (el valor por defecto) se deriva de la versión actual de
    la tabla: cada ejecución produce un lote distinto, que es lo que hace útil
    encadenar varias pasadas en una demostración.

    Con un valor explícito, la semilla es fija y el lote reproducible. Como las
    altas se aplican con ``upsert``, repetir el mismo lote es idempotente: no
    duplica pedidos.
    """
    if lote:
        return lote * 13
    fila = spark.sql(f"DESCRIBE HISTORY {tabla} LIMIT 1").select("version").collect()[0]
    return (int(fila["version"]) + 1) * 13


def main() -> None:
    args = parse_args()
    launcher, root = build_context(args.config, args.bundle_root)
    spark = launcher.spark
    cts = contratos(root, launcher.env)

    origen = cts["origen"]
    tabla = origen.full_name
    writer = TableWriter(origen)

    def con_timestamp(filas: list[dict]):
        return (
            spark.createDataFrame(filas)
            .withColumn("_updated_at", F.current_timestamp())
            .select([c.name for c in origen.columns])
        )

    if not _existe(spark, tabla):
        pedidos = generar_pedidos(PEDIDOS_INICIALES, semilla=42)
        writer.overwrite(con_timestamp(pedidos))
        print(f"Carga inicial: {len(pedidos)} pedidos en {tabla}")
        return

    # Lotes sucesivos: se parte del estado actual para que las transiciones
    # sean coherentes con lo que hay en la tabla.
    actuales = [fila.asDict() for fila in spark.table(tabla).collect()]
    semilla = _semilla(spark, tabla, args.lote)
    lote = generar_lote_cambios(actuales, semilla=semilla)

    # Las altas van por upsert y no por append: con una semilla explícita los
    # pedido_id generados son siempre los mismos, así que un append duplicaría
    # la clave primaria al repetir el lote.
    if lote["altas"]:
        writer.upsert(con_timestamp(lote["altas"]), keys=["pedido_id"])
    if lote["updates"]:
        writer.upsert(con_timestamp(lote["updates"]), keys=["pedido_id"])
    if lote["bajas"]:
        ids = ", ".join(f"'{i}'" for i in lote["bajas"])
        writer.delete(f"pedido_id IN ({ids})")

    print(
        f"Lote semilla={semilla} aplicado sobre {tabla} | "
        f"altas={len(lote['altas'])} updates={len(lote['updates'])} "
        f"bajas={len(lote['bajas'])}"
    )


if __name__ == "__main__":
    main()
