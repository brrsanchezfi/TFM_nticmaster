"""Entrypoint del Databricks Job: Landing -> Bronze."""
from customers.pipeline import DEFAULT_CONFIG, build_engine


def main(config_path: str = DEFAULT_CONFIG) -> None:
    _, engine = build_engine(config_path)
    failed = engine.ingest_bronze()
    if failed:
        raise RuntimeError(f"Ingesta a Bronze fallida en: {failed}")


if __name__ == "__main__":
    main()
