"""Tests de la lógica de negocio Gold — offline, solo Spark local."""
from retail_sales.transformations.gold_metrics import compute_kpis

FILAS = [
    # (venta_id, fecha, categoria, canal, cantidad, importe)
    ("v1", "2026-01-10", "Hogar", "online", 2, 20.0),
    ("v2", "2026-01-10", "Hogar", "online", 3, 40.0),
    ("v3", "2026-01-10", "Hogar", "tienda", 1, 10.0),
    ("v4", "2026-01-11", "Textil", "online", 5, 100.0),
]

COLUMNAS = ["venta_id", "fecha", "categoria", "canal", "cantidad", "importe"]


def _ventas(spark):
    return spark.createDataFrame(FILAS, COLUMNAS)


def test_agrupa_por_fecha_categoria_y_canal(spark):
    kpis = compute_kpis(_ventas(spark))
    # Hogar/online, Hogar/tienda y Textil/online → tres grupos distintos.
    assert kpis.count() == 3


def test_metricas_de_un_grupo(spark):
    kpis = compute_kpis(_ventas(spark))
    fila = kpis.filter("categoria = 'Hogar' AND canal = 'online'").collect()[0]

    assert fila["num_ventas"] == 2
    assert fila["unidades"] == 5
    assert fila["importe_total"] == 60.0
    assert fila["ticket_medio"] == 30.0


def test_fecha_se_convierte_a_tipo_date(spark):
    """En Silver la fecha es texto; Gold debe entregarla ya tipada."""
    kpis = compute_kpis(_ventas(spark))
    assert dict(kpis.dtypes)["fecha"] == "date"


def test_incluye_marca_de_generacion(spark):
    kpis = compute_kpis(_ventas(spark))
    assert kpis.filter("_generated_at IS NULL").count() == 0


def test_esquema_coincide_con_el_contrato_gold(spark):
    """El DataFrame debe traer exactamente las columnas que declara el contrato."""
    esperadas = {
        "fecha", "categoria", "canal", "num_ventas",
        "unidades", "importe_total", "ticket_medio", "_generated_at",
    }
    assert set(compute_kpis(_ventas(spark)).columns) == esperadas
