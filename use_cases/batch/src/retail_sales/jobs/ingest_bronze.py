"""Entrypoint del Databricks Job: Landing -> Bronze.

Sin ``--dataset`` procesa todos los contratos del directorio: las cinco
dimensiones y el hecho, en una sola pasada. Con ``--dataset`` procesa solo ese,
que es lo que permite al job separar la rama de dimensiones de la del hecho sin
duplicar código.

Con ``--dataset dimensiones`` la tarea hace **dos cosas distintas**, y por eso
van separadas por un banner en el log: primero simula el sistema maestro
publicando los catálogos en la landing —atrezo, no pipeline— y después ingiere
esa landing como haría con cualquier otro origen.
"""
from retail_sales.generators.publicar_dimensiones import publicar
from retail_sales.pipeline import DIMENSIONES, build_engine, parse_args


def main() -> None:
    args = parse_args()
    proceso = f"ingest_bronze_{args.dataset}" if args.dataset else "ingest_bronze"
    launcher, engine = build_engine(args.config, args.bundle_root, proceso=proceso)

    if args.dataset == "dimensiones":
        # Parte 1: el atrezo. En un entorno real esta llamada no existiría.
        publicar(launcher.spark, launcher.env)

        # Parte 2: el pipeline. Las cinco en una tarea porque son catálogos
        # diminutos y levantar una tarea por cada uno costaría más en
        # orquestación que en cómputo.
        failed = [d for d in DIMENSIONES if engine.ingest_bronze(d)]
    else:
        failed = engine.ingest_bronze(args.dataset)

    if failed:
        raise RuntimeError(f"Ingesta a Bronze fallida en: {failed}")


if __name__ == "__main__":
    main()
