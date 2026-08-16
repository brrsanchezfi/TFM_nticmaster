"""Entrypoint del Databricks Job: Bronze -> Silver."""
from weather_events.pipeline import DEFAULT_CONFIG, build_engine


def main(config_path: str = DEFAULT_CONFIG) -> None:
    _, engine = build_engine(config_path)
    failed = engine.promote_silver()
    if failed:
        raise RuntimeError(f"Promoción a Silver fallida en: {failed}")


if __name__ == "__main__":
    main()
