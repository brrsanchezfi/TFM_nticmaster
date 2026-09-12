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
        .appName("customers-tests")
        # Los datasets de prueba son diminutos: repartirlos en mas particiones
        # solo anade coste de planificacion.
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
