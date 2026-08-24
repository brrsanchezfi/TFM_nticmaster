"""Lógica de negocio del dominio 'weather_events' para construir la capa Gold.

Agrega las observaciones en ventanas horarias por ciudad. La escritura se
delega en DKOps (`TableWriter`), que valida el DataFrame contra el contrato
antes de escribir.
"""
from __future__ import annotations

from pathlib import Path

from DKOps.table_governance import TableWriter, load_contract
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

GOLD_CONTRACT = "contracts/tables/gold/metricas.json"

SILVER_SCHEMA = "streaming"
SILVER_TABLE = "eventos"


def compute_metricas(eventos: DataFrame) -> DataFrame:
    """Agrega las observaciones por ciudad y ventana horaria.

    Se separa de `build()` a propósito: recibe y devuelve DataFrames, sin tocar
    catálogos ni contratos, de modo que puede testearse con Spark local.
    """
    return (
        eventos
        # En Silver la hora es texto, fiel al JSON de la API. Aquí pasa a
        # timestamp y se trunca a la hora, que es la ventana de agregación.
        .withColumn("ventana", F.date_trunc("hour", F.to_timestamp("hora")))
        .groupBy("ciudad", "ventana")
        .agg(
            F.count("*").cast("long").alias("num_lecturas"),
            F.round(F.avg("temperatura"), 2).alias("temperatura_media"),
            F.min("temperatura").alias("temperatura_min"),
            F.max("temperatura").alias("temperatura_max"),
            F.round(F.avg("humedad"), 2).alias("humedad_media"),
            F.max("viento").alias("viento_max"),
        )
        .withColumn("_generated_at", F.current_timestamp())
    )


def build(spark: SparkSession, env, bundle_root: Path) -> None:
    """Construye la tabla Gold de métricas a partir de Silver."""
    silver_table = f"{env.get_catalog('silver')}.{SILVER_SCHEMA}.{SILVER_TABLE}"
    metricas = compute_metricas(spark.table(silver_table))

    contract = load_contract(bundle_root / GOLD_CONTRACT, env=env)
    # overwrite y no append: el agregado es una foto completa del histórico,
    # así que reejecutar el job no duplica métricas.
    TableWriter(contract).overwrite(metricas)
