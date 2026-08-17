"""Entrypoint del Databricks Job: Silver -> Gold.

La lógica de negocio del dominio vive en transformations/, no aquí: este
módulo solo orquesta.
"""
from customers.pipeline import build_engine, parse_args
from customers.transformations import gold_metrics


def main() -> None:
    args = parse_args()
    launcher, _ = build_engine(args.config, args.bundle_root)
    gold_metrics.build(launcher.spark, launcher.env)


if __name__ == "__main__":
    main()
