"""Tests del generador sintético — sin Spark, puro Python."""
import json

from retail_sales.generators.generate_sales import escribir_jsonl, generar_ventas


def test_es_reproducible_con_la_misma_semilla():
    a = generar_ventas(50, semilla=7)
    b = generar_ventas(50, semilla=7)
    assert a == b


def test_semillas_distintas_dan_datasets_distintos():
    a = generar_ventas(50, semilla=1)
    b = generar_ventas(50, semilla=2)
    assert a != b


def test_genera_duplicados_para_ejercitar_el_merge():
    """Sin venta_id repetidos, la estrategia full_merge no demostraría nada."""
    ventas = generar_ventas(100, semilla=3, duplicados=0.1)
    ids = [v["venta_id"] for v in ventas]

    assert len(ventas) == 110
    assert len(set(ids)) == 100


def test_importe_es_coherente_con_cantidad_y_precio():
    for venta in generar_ventas(100, semilla=5):
        esperado = round(venta["cantidad"] * venta["precio_unitario"], 2)
        assert abs(venta["importe"] - esperado) < 0.01


def test_escribe_json_lines_legible(tmp_path):
    ventas = generar_ventas(10, semilla=11)
    fichero = escribir_jsonl(ventas, tmp_path / "ventas")

    lineas = fichero.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 10
    # Cada línea debe ser un objeto JSON independiente: es lo que espera el
    # lector de DKOps con multiLine=false.
    assert all(json.loads(linea)["venta_id"] for linea in lineas)
