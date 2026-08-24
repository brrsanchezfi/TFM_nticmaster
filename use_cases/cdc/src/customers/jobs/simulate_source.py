"""Entrypoint del Databricks Job: el sistema origen exporta sus cambios.

Deja en la landing un fichero JSON con los eventos I/U/D del lote. Es el
sustituto de Change Tracking de Azure SQL, que no se puede usar porque el
provider Microsoft.Sql no está registrado en la suscripción.

La primera ejecución da de alta la cartera inicial; las siguientes emiten
altas, modificaciones y bajas sobre los clientes vigentes.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from customers.generators.simulate_changes import carga_inicial, lote_cambios
from customers.pipeline import build_engine, parse_args

CLIENTES_INICIALES = 200

# Campos que existen en el sistema origen. Silver se lee para saber qué
# clientes siguen vigentes, pero sus columnas internas (is_deleted,
# _silver_modified_at) no pueden viajar de vuelta a la landing: un sistema
# origen no conoce la estructura interna del almacén. Si se colasen, Auto
# Loader las vería como campos nuevos y abortaría el stream.
CAMPOS_ORIGEN = ["cliente_id", "nombre", "email", "ciudad", "segmento", "fecha_alta"]


def main() -> None:
    args = parse_args()
    launcher, _ = build_engine(args.config, args.bundle_root)
    spark, env = launcher.spark, launcher.env

    silver = f"{env.get_catalog('silver')}.cdc.clientes_current"
    # La semilla explícita hace el lote reproducible; con 0 se deriva del reloj
    # para que cada ejecución emita cambios distintos.
    semilla = args.lote or int(time.time()) % 100000

    if not spark.catalog.tableExists(silver):
        eventos = carga_inicial(CLIENTES_INICIALES, semilla=42)
        detalle = f"carga inicial de {len(eventos)} clientes"
    else:
        # Solo los clientes vigentes pueden modificarse o darse de baja: uno
        # que ya está de baja no vuelve a emitir eventos.
        # 'is_deleted IS NOT TRUE' y no 'NOT is_deleted': con lógica de tres
        # valores, NOT NULL no es TRUE, así que un solo nulo en la columna
        # dejaría fuera a esa fila. Si acaban siendo todas nulas, el filtro
        # devuelve cero clientes y el generador emite lotes degenerados sin que
        # nada falle — un fallo silencioso que ya ocurrió una vez.
        vigentes = [
            fila.asDict()
            for fila in (
                spark.table(silver)
                .filter("is_deleted IS NOT TRUE")
                .select(*CAMPOS_ORIGEN)
                .collect()
            )
        ]

        if not vigentes:
            raise RuntimeError(
                f"{silver} no devolvió ningún cliente vigente. Sin cartera de "
                "partida no se pueden generar modificaciones ni bajas: revisa "
                "la columna is_deleted antes de seguir."
            )
        eventos = lote_cambios(vigentes, semilla=semilla)
        detalle = f"lote de {len(eventos)} eventos (semilla={semilla})"

    destino = f"{env.get_path('landing')}/clientes"
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    (
        spark.createDataFrame(eventos)
        .coalesce(1)
        .write.mode("append")
        .json(f"{destino}/lote={marca}")
    )

    reparto = {}
    for evento in eventos:
        reparto[evento["op_type"]] = reparto.get(evento["op_type"], 0) + 1

    print(f"{detalle} -> {destino}/lote={marca} | reparto={reparto}")


if __name__ == "__main__":
    main()
