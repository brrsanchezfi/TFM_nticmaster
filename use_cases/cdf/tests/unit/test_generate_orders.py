"""Tests del generador de pedidos y lotes de cambios — sin Spark."""
from orders.generators.generate_orders import (
    TRANSICIONES,
    generar_lote_cambios,
    generar_pedidos,
)


def test_es_reproducible_con_la_misma_semilla():
    assert generar_pedidos(30, semilla=5) == generar_pedidos(30, semilla=5)


def test_la_carga_inicial_nace_entera_en_estado_nuevo():
    assert {p["estado"] for p in generar_pedidos(50)} == {"nuevo"}


def test_el_lote_trae_las_tres_operaciones():
    lote = generar_lote_cambios(generar_pedidos(100), semilla=3)
    assert lote["altas"] and lote["updates"] and lote["bajas"]


def test_los_updates_respetan_el_ciclo_de_vida():
    """Un pedido entregado no puede volver a 'nuevo': si el generador
    produjera transiciones imposibles, el agregado dejaría de ser creíble."""
    pedidos = generar_pedidos(100)
    originales = {p["pedido_id"]: p["estado"] for p in pedidos}

    for actualizado in generar_lote_cambios(pedidos, semilla=9)["updates"]:
        anterior = originales[actualizado["pedido_id"]]
        assert actualizado["estado"] in TRANSICIONES[anterior]


def test_una_baja_nunca_coincide_con_un_update():
    """Borrar y actualizar la misma fila en el mismo lote haría el resultado
    dependiente del orden de aplicación."""
    lote = generar_lote_cambios(generar_pedidos(100), semilla=11)
    actualizados = {p["pedido_id"] for p in lote["updates"]}
    assert not actualizados & set(lote["bajas"])


def test_las_altas_no_reutilizan_identificadores_existentes():
    pedidos = generar_pedidos(100)
    existentes = {p["pedido_id"] for p in pedidos}
    altas = {p["pedido_id"] for p in generar_lote_cambios(pedidos, semilla=13)["altas"]}
    assert not altas & existentes
