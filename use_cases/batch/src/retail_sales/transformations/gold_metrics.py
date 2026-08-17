"""Lógica de negocio del dominio 'retail_sales' para construir la capa Gold.

Esta es la parte específica de ESTE caso de uso, no genérica de DKOps: aquí
van las reglas de negocio, agregaciones y métricas concretas del dominio.
"""
from __future__ import annotations


def build(spark, env) -> None:
    """Construye las tablas Gold del dominio.

    Parámetros
    ----------
    spark : SparkSession activa, creada por el Launcher de DKOps.
    env   : EnvironmentConfig, resuelve nombres de catálogo por entorno.
    """
    raise NotImplementedError("Definir agregaciones de negocio de retail_sales")
