"""Entrypoint del Databricks Job: Bronze -> Silver.

Sin ``--dataset`` promociona todos los contratos del directorio: las cinco
dimensiones y el hecho. Con ``--dataset`` promociona solo ese.

Las seis promociones usan la misma estrategia, ``full_merge``, declarada en el
contrato. Es el resultado más ilustrativo del caso: dimensiones y hecho se
consolidan igual, cada uno por su clave, y el código no distingue entre ellos.
"""
from retail_sales.pipeline import DIMENSIONES, build_engine, parse_args


def main() -> None:
    args = parse_args()
    proceso = f"promote_silver_{args.dataset}" if args.dataset else "promote_silver"
    _, engine = build_engine(args.config, args.bundle_root, proceso=proceso)

    if args.dataset == "dimensiones":
        failed = [d for d in DIMENSIONES if engine.promote_silver(d)]
    else:
        failed = engine.promote_silver(args.dataset)

    if failed:
        raise RuntimeError(f"Promoción a Silver fallida en: {failed}")


if __name__ == "__main__":
    main()
