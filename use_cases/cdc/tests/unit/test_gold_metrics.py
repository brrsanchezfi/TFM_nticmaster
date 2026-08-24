"""Tests de la lógica Gold del caso CDC — offline, solo Spark local."""
from customers.transformations.gold_metrics import compute_cartera, compute_historico

COLS_SILVER = ["cliente_id", "segmento", "ciudad", "is_deleted"]

CLIENTES = [
    ("CLI-1", "retail", "Madrid", False),
    ("CLI-2", "retail", "Madrid", False),
    ("CLI-3", "retail", "Madrid", True),
    ("CLI-4", "premium", "Bilbao", False),
]

COLS_BRONZE = ["cliente_id", "op_type", "op_ts"]

EVENTOS = [
    ("CLI-1", "I", "2026-08-20T10:00:00"),
    ("CLI-2", "I", "2026-08-20T11:00:00"),
    ("CLI-1", "U", "2026-08-20T12:00:00"),
    ("CLI-3", "D", "2026-08-21T09:00:00"),
]


def test_separa_activos_de_bajas(spark):
    """Es lo que aporta el soft-delete: con borrado físico, 'bajas' sería
    siempre cero porque esas filas no existirían."""
    cartera = compute_cartera(spark.createDataFrame(CLIENTES, COLS_SILVER))
    fila = cartera.filter("segmento = 'retail' AND ciudad = 'Madrid'").collect()[0]

    assert fila["activos"] == 2
    assert fila["bajas"] == 1
    assert fila["total"] == 3


def test_agrupa_por_segmento_y_ciudad(spark):
    cartera = compute_cartera(spark.createDataFrame(CLIENTES, COLS_SILVER))
    assert cartera.count() == 2


def test_historico_cuenta_operaciones_por_dia_y_tipo(spark):
    historico = compute_historico(spark.createDataFrame(EVENTOS, COLS_BRONZE))

    altas = historico.filter("op_type = 'I'").collect()[0]
    assert altas["operaciones"] == 2
    assert altas["clientes"] == 2

    assert historico.filter("op_type = 'D'").collect()[0]["operaciones"] == 1


def test_el_historico_separa_dias(spark):
    """Los eventos del 20 y del 21 no pueden mezclarse en la misma fila."""
    historico = compute_historico(spark.createDataFrame(EVENTOS, COLS_BRONZE))
    fechas = {str(f["fecha"]) for f in historico.collect()}
    assert fechas == {"2026-08-20", "2026-08-21"}


def test_esquemas_coinciden_con_los_contratos(spark):
    cartera = compute_cartera(spark.createDataFrame(CLIENTES, COLS_SILVER))
    assert set(cartera.columns) == {
        "segmento", "ciudad", "activos", "bajas", "total", "_generated_at",
    }

    historico = compute_historico(spark.createDataFrame(EVENTOS, COLS_BRONZE))
    assert set(historico.columns) == {
        "fecha", "op_type", "operaciones", "clientes", "_generated_at",
    }
