"""Entrypoint invocado por el Databricks Job: Silver -> Gold.

La lógica de negocio específica del dominio (agregaciones, KPIs) vive en
transformations/, no aquí — este módulo solo orquesta.
"""
from customers.transformations import gold_metrics


def main() -> None:
    gold_metrics.build()


if __name__ == "__main__":
    main()
