"""Entrypoint del Databricks Job: Landing -> Bronze."""
from retail_sales.pipeline import build_engine, parse_args


def main() -> None:
    args = parse_args()
    _, engine = build_engine(args.config, args.bundle_root)
    failed = engine.ingest_bronze()
    if failed:
        raise RuntimeError(f"Ingesta a Bronze fallida en: {failed}")


if __name__ == "__main__":
    main()
