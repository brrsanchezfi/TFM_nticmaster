"""Propagación incremental de cambios a Gold usando Change Data Feed.

La idea del caso: en lugar de reconstruir el agregado leyendo la tabla entera,
se pregunta al Change Data Feed *qué ha cambiado* desde la última ejecución y
se recalculan únicamente los grupos afectados.

Las funciones de este módulo reciben y devuelven DataFrames, sin tocar
catálogos ni contratos, para poder testearlas con Spark local.
"""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Tipos de cambio que emite Delta en el feed.
CHANGE_TYPES = ("insert", "update_preimage", "update_postimage", "delete")

GROUP_KEY = "estado"


def estados_afectados(cambios: DataFrame) -> list[str]:
    """Devuelve los estados que tocó el feed, incluidos los que se abandonaron.

    Un pedido que pasa de 'nuevo' a 'pagado' genera dos filas: `update_preimage`
    con el estado viejo y `update_postimage` con el nuevo. Ambos agregados
    quedan desactualizados, así que hay que recalcular los dos.

    Ignorar las preimágenes sería el error clásico: el estado de origen se
    quedaría con un pedido de más para siempre.
    """
    if cambios.isEmpty():
        return []

    filas = (
        cambios
        .select(F.col(GROUP_KEY))
        .where(F.col(GROUP_KEY).isNotNull())
        .distinct()
        .collect()
    )
    return sorted(fila[GROUP_KEY] for fila in filas)


def recalcular_agregado(pedidos: DataFrame, estados: list[str]) -> DataFrame:
    """Recalcula el agregado, pero solo para los estados indicados.

    Se recalcula desde la tabla origen —no desde el propio feed— porque el
    valor correcto de un grupo es el que resulta del estado actual de los
    datos. Aplicar deltas sumando y restando importes del feed también
    funcionaría, pero es mucho más fácil de descuadrar ante reprocesos.
    """
    return (
        pedidos
        .where(F.col(GROUP_KEY).isin(estados))
        .groupBy(GROUP_KEY)
        .agg(
            F.count("*").cast("long").alias("num_pedidos"),
            F.sum("unidades").cast("long").alias("unidades"),
            F.round(F.sum("importe"), 2).alias("importe_total"),
        )
        .withColumn("_recalculado_at", F.current_timestamp())
    )


def estados_vaciados(agregado_nuevo: DataFrame, estados: list[str]) -> list[str]:
    """Estados afectados que se han quedado sin ningún pedido.

    Ocurre cuando el último pedido de un estado se borra o cambia de estado.
    Como no aparecen en el recálculo, un `MERGE` nunca los tocaría y su fila
    en Gold quedaría congelada con un valor obsoleto: hay que borrarla
    explícitamente.
    """
    if not estados:
        return []
    con_datos = {fila[GROUP_KEY] for fila in agregado_nuevo.select(GROUP_KEY).collect()}
    return sorted(set(estados) - con_datos)
