"""Fixtures compartidas de los tests.

Spark en local, sin Databricks y sin Unity Catalog. Los tests solo ejercitan
las funciones de negocio, que reciben y devuelven DataFrames, asi que no hace
falta Delta ni acceso al lago.
"""
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("orders-tests")
        # Los datasets de prueba son diminutos: repartirlos en mas particiones
        # solo anade coste de planificacion.
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture
def pedidos(spark):
    """Tabla origen simulada: cinco pedidos repartidos en tres estados."""
    filas = [
        ("p1", "nuevo", 2, 100.0),
        ("p2", "nuevo", 1, 50.0),
        ("p3", "pagado", 3, 200.0),
        ("p4", "enviado", 1, 30.0),
        ("p5", "enviado", 4, 70.0),
    ]
    return spark.createDataFrame(filas, ["pedido_id", "estado", "unidades", "importe"])
