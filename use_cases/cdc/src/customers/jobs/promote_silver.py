"""Entrypoint del Databricks Job: Bronze -> Silver."""
from customers.pipeline import build_engine, parse_args


def main() -> None:
    args = parse_args()
    _, engine = build_engine(args.config, args.bundle_root)
    failed = engine.promote_silver()
    if failed:
        raise RuntimeError(f"Promoción a Silver fallida en: {failed}")


if __name__ == "__main__":
    main()
