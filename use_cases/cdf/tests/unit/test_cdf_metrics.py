"""Tests de la propagación incremental — offline, solo Spark local."""
from orders.transformations.cdf_metrics import (
    estados_afectados,
    estados_vaciados,
    recalcular_agregado,
)

COLS_CAMBIO = ["pedido_id", "estado", "unidades", "importe", "_change_type"]


def _cambios(spark, filas):
    return spark.createDataFrame(filas, COLS_CAMBIO)


def test_sin_cambios_no_hay_estados_afectados(spark):
    vacio = spark.createDataFrame([], ",".join(f"{c} string" for c in COLS_CAMBIO))
    assert estados_afectados(vacio) == []


def test_un_insert_afecta_solo_a_su_estado(spark):
    cambios = _cambios(spark, [("p9", "nuevo", 1, 10.0, "insert")])
    assert estados_afectados(cambios) == ["nuevo"]


def test_un_update_afecta_al_estado_viejo_y_al_nuevo(spark):
    """El caso que más fácil se escapa: sin la preimagen, el estado de origen
    se quedaría con un pedido de más para siempre."""
    cambios = _cambios(spark, [
        ("p1", "nuevo", 2, 100.0, "update_preimage"),
        ("p1", "pagado", 2, 100.0, "update_postimage"),
    ])
    assert estados_afectados(cambios) == ["nuevo", "pagado"]


def test_un_delete_afecta_a_su_estado(spark):
    cambios = _cambios(spark, [("p4", "enviado", 1, 30.0, "delete")])
    assert estados_afectados(cambios) == ["enviado"]


def test_recalcula_solo_los_estados_indicados(spark, pedidos):
    """Lo que hace incremental al proceso: 'pagado' no se toca."""
    agregado = recalcular_agregado(pedidos, ["nuevo", "enviado"])
    assert sorted(f["estado"] for f in agregado.collect()) == ["enviado", "nuevo"]


def test_metricas_del_agregado(spark, pedidos):
    agregado = recalcular_agregado(pedidos, ["nuevo"])
    fila = agregado.collect()[0]

    assert fila["num_pedidos"] == 2
    assert fila["unidades"] == 3
    assert fila["importe_total"] == 150.0


def test_detecta_estados_que_se_quedan_sin_pedidos(spark, pedidos):
    """'cancelado' fue afectado pero no tiene pedidos: su fila en Gold debe
    borrarse, porque un MERGE nunca la tocaría."""
    agregado = recalcular_agregado(pedidos, ["nuevo", "cancelado"])
    assert estados_vaciados(agregado, ["nuevo", "cancelado"]) == ["cancelado"]


def test_sin_estados_afectados_no_hay_nada_que_vaciar(spark, pedidos):
    agregado = recalcular_agregado(pedidos, [])
    assert estados_vaciados(agregado, []) == []


def test_esquema_coincide_con_el_contrato_gold(spark, pedidos):
    esperadas = {"estado", "num_pedidos", "unidades", "importe_total", "_recalculado_at"}
    assert set(recalcular_agregado(pedidos, ["nuevo"]).columns) == esperadas
