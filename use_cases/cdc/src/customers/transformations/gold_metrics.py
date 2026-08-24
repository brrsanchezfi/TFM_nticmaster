"""Lógica de negocio del dominio 'customers' para construir la capa Gold.

Dos tablas con propósitos distintos:

- `clientes_activos` sale de Silver, que ya tiene la foto actual de cada
  cliente. Responde a "cómo está mi cartera ahora".
- `historico_cambios` sale de Bronze, que conserva todos los eventos. Responde
  a "qué ha pasado". Silver no sirve para esto: ha colapsado los eventos.

Esa separación es la razón de ser de la arquitectura por capas en un caso CDC.
"""
from __future__ import annotations

from pathlib import Path

from DKOps.table_governance import TableWriter, load_contract
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

CONTRATO_ACTIVOS = "contracts/tables/gold/clientes_activos.json"
CONTRATO_HISTORICO = "contracts/tables/gold/historico_cambios.json"


def compute_cartera(clientes: DataFrame) -> DataFrame:
    """Cartera por segmento y ciudad, separando activos de bajas.

    Poder contar las bajas es precisamente lo que aporta el soft-delete: con un
    borrado físico esas filas no existirían y la columna sería siempre cero.
    """
    return (
        clientes
        .groupBy("segmento", "ciudad")
        .agg(
            F.sum(F.when(~F.col("is_deleted"), 1).otherwise(0)).cast("long").alias("activos"),
            F.sum(F.when(F.col("is_deleted"), 1).otherwise(0)).cast("long").alias("bajas"),
            F.count("*").cast("long").alias("total"),
        )
        .withColumn("_generated_at", F.current_timestamp())
    )


def compute_historico(eventos: DataFrame) -> DataFrame:
    """Actividad diaria del sistema origen, por tipo de operación."""
    return (
        eventos
        .withColumn("fecha", F.to_date(F.to_timestamp("op_ts")))
        .groupBy("fecha", "op_type")
        .agg(
            F.count("*").cast("long").alias("operaciones"),
            F.countDistinct("cliente_id").cast("long").alias("clientes"),
        )
        .withColumn("_generated_at", F.current_timestamp())
    )


def build(spark: SparkSession, env, bundle_root: Path) -> None:
    """Construye las dos tablas Gold del dominio."""
    silver = f"{env.get_catalog('silver')}.cdc.clientes_current"
    bronze = f"{env.get_catalog('bronze')}.cdc.clientes_raw"

    cartera = compute_cartera(spark.table(silver))
    historico = compute_historico(spark.table(bronze))

    # overwrite en ambas: son fotos completas y el volumen de la PoC lo
    # permite, así que reejecutar el job no duplica nada.
    TableWriter(load_contract(bundle_root / CONTRATO_ACTIVOS, env=env)).overwrite(cartera)
    TableWriter(load_contract(bundle_root / CONTRATO_HISTORICO, env=env)).overwrite(historico)
