"""Lógica de negocio del dominio 'retail_sales' para construir la capa Gold.

Esta es la parte específica de ESTE caso de uso, no genérica de DKOps: aquí
van las reglas de negocio, agregaciones y métricas concretas del dominio.

La escritura sí se delega en DKOps (`TableWriter`), que valida el DataFrame
contra el contrato de tabla antes de escribir. Así el esquema de Gold está
gobernado por el mismo mecanismo que Bronze y Silver.
"""
from __future__ import annotations

from pathlib import Path

from DKOps.table_governance import TableWriter, load_contract
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

GOLD_CONTRACT = "contracts/tables/gold/ventas_kpis.json"

SILVER_SCHEMA = "batch"
SILVER_TABLE = "ventas"


def compute_kpis(ventas: DataFrame) -> DataFrame:
    """Agrega las ventas curadas en KPIs diarios por categoría y canal.

    Se separa de `build()` a propósito: recibe y devuelve DataFrames, sin
    tocar catálogos ni contratos, de modo que puede testearse en local con
    Spark sin necesidad de Databricks ni de Unity Catalog.
    """
    return (
        ventas
        # En Silver la fecha sigue siendo texto, fiel al JSON de origen.
        # Es en Gold, la capa de consumo, donde pasa a ser un tipo con el que
        # se pueda filtrar y ordenar de verdad.
        .withColumn("fecha", F.to_date("fecha"))
        .groupBy("fecha", "categoria", "canal")
        .agg(
            F.count("*").alias("num_ventas"),
            F.sum("cantidad").cast("long").alias("unidades"),
            F.round(F.sum("importe"), 2).alias("importe_total"),
            F.round(F.avg("importe"), 2).alias("ticket_medio"),
        )
        .withColumn("_generated_at", F.current_timestamp())
    )


def build(spark: SparkSession, env, bundle_root: Path) -> None:
    """Construye la tabla Gold de KPIs a partir de Silver.

    Parámetros
    ----------
    spark       : SparkSession activa, creada por el Launcher de DKOps.
    env         : EnvironmentConfig, resuelve los nombres de catálogo por entorno.
    bundle_root : raíz del bundle desplegado, donde vive contracts/.
    """
    silver_table = f"{env.get_catalog('silver')}.{SILVER_SCHEMA}.{SILVER_TABLE}"
    ventas = spark.table(silver_table)

    kpis = compute_kpis(ventas)

    contract = load_contract(bundle_root / GOLD_CONTRACT, env=env)
    # overwrite y no append: el agregado es una foto completa del histórico,
    # así que reejecutar el job dos veces no duplica KPIs.
    TableWriter(contract).overwrite(kpis)
