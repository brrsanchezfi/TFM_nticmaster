"""Fixtures compartidas. Spark local, sin Databricks ni Unity Catalog."""
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("orders-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
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
