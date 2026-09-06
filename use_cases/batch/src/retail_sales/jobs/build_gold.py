"""Entrypoint del Databricks Job: Silver -> Gold.

La lógica de negocio del dominio vive en transformations/, no aquí: este
módulo solo orquesta.
"""
from retail_sales.pipeline import build_engine, parse_args, resolve_bundle_root
from retail_sales.transformations import gold_metrics


def main() -> None:
    args = parse_args()
    launcher, _ = build_engine(args.config, args.bundle_root, proceso="build_gold")
    gold_metrics.build(
        launcher.spark,
        launcher.env,
        resolve_bundle_root(args.bundle_root),
    )


if __name__ == "__main__":
    main()
