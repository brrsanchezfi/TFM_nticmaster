"""Fixtures compartidas. Spark local, sin Databricks ni Unity Catalog."""
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("retail_sales-tests")
        # Una sola partición: los datasets de test son diminutos y así los
        # tests tardan segundos en vez de decenas de segundos.
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()
