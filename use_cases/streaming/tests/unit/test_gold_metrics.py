"""Tests de la lógica de negocio Gold — offline, solo Spark local."""
from weather_events.transformations.gold_metrics import compute_metricas

COLUMNAS = ["ciudad", "hora", "temperatura", "humedad", "viento"]

FILAS = [
    # Dos lecturas dentro de la misma hora, en Madrid
    ("Madrid", "2026-08-18T10:00", 24.0, 40, 12.0),
    ("Madrid", "2026-08-18T10:30", 26.0, 50, 18.0),
    # Otra hora distinta, misma ciudad
    ("Madrid", "2026-08-18T11:00", 28.0, 45, 9.0),
    # Otra ciudad
    ("Bilbao", "2026-08-18T10:15", 19.0, 70, 22.0),
]


def _eventos(spark):
    return spark.createDataFrame(FILAS, COLUMNAS)


def test_agrupa_por_ciudad_y_ventana_horaria(spark):
    """Las dos lecturas de las 10:00 y 10:30 caen en la misma ventana."""
    metricas = compute_metricas(_eventos(spark))
    assert metricas.count() == 3


def test_metricas_de_una_ventana(spark):
    metricas = compute_metricas(_eventos(spark))
    fila = (
        metricas
        .filter("ciudad = 'Madrid' AND hour(ventana) = 10")
        .collect()[0]
    )

    assert fila["num_lecturas"] == 2
    assert fila["temperatura_media"] == 25.0
    assert fila["temperatura_min"] == 24.0
    assert fila["temperatura_max"] == 26.0
    assert fila["viento_max"] == 18.0


def test_la_ventana_se_trunca_a_la_hora(spark):
    """En Silver la hora es texto; Gold debe entregar un timestamp truncado."""
    metricas = compute_metricas(_eventos(spark))
    assert dict(metricas.dtypes)["ventana"] == "timestamp"

    minutos = {f["ventana"].minute for f in metricas.collect()}
    assert minutos == {0}


def test_esquema_coincide_con_el_contrato_gold(spark):
    esperadas = {
        "ciudad", "ventana", "num_lecturas", "temperatura_media",
        "temperatura_min", "temperatura_max", "humedad_media",
        "viento_max", "_generated_at",
    }
    assert set(compute_metricas(_eventos(spark)).columns) == esperadas
