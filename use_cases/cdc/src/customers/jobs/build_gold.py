"""Entrypoint del Databricks Job: Silver/Bronze -> Gold.

La lógica de negocio del dominio vive en transformations/, no aquí: este
módulo solo orquesta.
"""
from customers.pipeline import build_engine, parse_args, resolve_bundle_root
from customers.transformations import gold_metrics


def main() -> None:
    args = parse_args()
    launcher, _ = build_engine(args.config, args.bundle_root)
    gold_metrics.build(
        launcher.spark,
        launcher.env,
        resolve_bundle_root(args.bundle_root),
    )


if __name__ == "__main__":
    main()
