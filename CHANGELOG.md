# Changelog

## [Unreleased]
- Scaffolding inicial del repositorio.
- Fase 2 — Infraestructura como código (Terraform):
  - Inventario del entorno real: el TFM se despliega sobre el workspace
    corporativo compartido `lakehousedkops`, no sobre una suscripción vacía.
  - Módulo `unity_catalog`: catálogos `bronze_tfm`/`silver_tfm`/`gold_tfm` y un
    schema por caso de uso, aislados de los catálogos del equipo.
  - Módulo `sql_database`: Azure SQL serverless para el caso CDC, con
    autenticación solo Entra ID. Desactivado por defecto: el provider
    `Microsoft.Sql` está sin registrar en la suscripción.
  - Los recursos preexistentes (RG, storage, workspace, metastore) se leen con
    `data` sources; el plan confirma `0 to change, 0 to destroy`.
  - Se descartan los módulos `resource_group`, `storage`,
    `databricks_workspace` y `networking`: nada de eso lo crea el TFM.
  - Las configuraciones `dev` de los 4 casos de uso apuntan a los catálogos
    `*_tfm`.
- Fase 4 — Integración de DKOps como dependencia:
  - Versión fijada en el tag `v0.3.0` (`platform/dkops_version.txt`).
  - Corregido el nombre del paquete importable: es `DKOps`, no `dkops`. Los 8
    entrypoints del scaffold no habrían importado.
  - Sustituido el inexistente `IngestionEngine.from_spark()` por el cableado
    real: `IngestionContractLoader` + `IngestionEngine`, en un nuevo módulo
    `pipeline.py` por caso de uso.
  - El caso streaming usa `run_streaming()` (Auto Loader con trigger
    `availableNow`) en lugar de `ingest_bronze()`.
  - Los `pyproject.toml` delegan en el extra `dkops[local]` en vez de repetir
    las versiones de pyspark/delta-spark.
  - Verificado: los 4 casos de uso importan y resuelven `build_engine`.
- Fase 3 — Unity Catalog desplegado:
  - Creados `bronze_tfm`, `silver_tfm` y `gold_tfm` con `storage_root` en la
    carpeta `tfm/` del contenedor de su capa, más 12 schemas (uno por caso de
    uso). Hecho por API, no con `terraform apply`: el state de `infra/` queda
    vacío y habría que importar los recursos si se quisiera gestionar desde ahí.
- Asset Bundles configurados contra el workspace real:
  - Runtime `16.4.x-scala2.12` (Spark 3.5.2), el LTS más próximo al
    `pyspark 3.5.3` que fija DKOps; los LTS más nuevos van con Spark 4.x.
  - Job cluster single-node, spot con fallback y `data_security_mode`
    `SINGLE_USER` (requisito de Unity Catalog para wheel tasks). No se adjunta
    la policy "Job Compute" porque prohíbe `spark.databricks.cluster.profile`.
  - Un único job cluster compartido por las tres tareas, en vez de tres
    arranques.
  - Añadidos los `[project.scripts]`: `python_wheel_task` necesita un entry
    point por tarea; el scaffold declaraba `main` en las tres.
  - La raíz del bundle se pasa por `--bundle-root ${workspace.file_path}`: el
    wheel se instala en site-packages y no puede deducirla desde `__file__`.
  - `databricks bundle validate -t dev` correcto en los cuatro bundles.
- Fase 5 — Caso de uso Batch (retail_sales):
  - Generador de ventas sintéticas reproducible por semilla, que emite a
    propósito un 5% de ventas repetidas para que la estrategia `full_merge`
    tenga algo que resolver.
  - Cinco contratos: tablas Bronze/Silver/Gold y las dos ingestas.
  - Bronze particionado por `_ingested_date`, que es lo que permite a DKOps
    hacer *partition overwrite* y que la ingesta sea idempotente.
  - `compute_kpis()` separada de `build()` para poder testear la lógica de
    negocio sin Databricks ni Unity Catalog.
  - El log de operaciones pasa a ADLS: en `/tmp` se perdía al apagarse el
    job cluster.
  - 10 tests en verde, incluidos los que levantan Spark local.
  - Documentado en `docs/casos_uso/batch.md`.
  - **Ejecutado end-to-end en Databricks**: 525 filas en Landing y Bronze,
    500 en Silver (las 25 reemisiones colapsadas por `full_merge`) y 249
    agregados en Gold. Es la primera vez que un dato recorre la cadena
    completa Terraform → Unity Catalog → DKOps → Asset Bundle.
  - Correcciones necesarias para que el despliegue y la ejecución funcionaran:
    - `first_on_demand` pasa a 1: en single-node la única VM es el driver y
      Azure exige que sea on-demand. En consecuencia, no hay ahorro por spot
      en esta configuración.
    - `EXECUTION_ENVIRONMENT` pasa a `local` en los 4 casos de uso: para DKOps
      `databricks` significa Databricks Connect desde fuera y exige
      `CLUSTER_ID`.
    - Las claves de `environments` pasan a ser el `workspace_id`: es así como
      DKOps resuelve el entorno cuando corre dentro de Databricks.
    - El contrato de Silver deja de declarar `_silver_created_at`: la
      estrategia `full_merge` no la genera, pese al nombre en plural del flag
      `add_silver_timestamps`. Reportado como incidencia en DKOps.
  - Creado el volumen externo `bronze_tfm.batch.landing`: el usuario no tiene
    rol de datos sobre el storage, así que la subida de ficheros se gobierna
    por Unity Catalog en lugar de por RBAC de Azure.
  - Descartado el riesgo de egress: los job clusters sí alcanzan GitHub para
    instalar DKOps desde el tag.
  - Capa de consumo: dashboard AI/BI declarado en el bundle y versionado en
    `dashboards/ventas_kpis.lvdash.json`. Se despliega con el mismo
    `bundle deploy` que el job, así que la capa de consumo también es
    reproducible desde el repositorio. Incluye un gráfico de filas por capa
    que hace visible la deduplicación de Bronze a Silver. Reutiliza el SQL
    Warehouse serverless existente y no embebe credenciales, de modo que cada
    usuario lo consulta con sus permisos de Unity Catalog.
- Fase 6 — Caso de uso CDF (orders):
  - Tabla origen propia `silver_tfm.cdf.pedidos` con `change_data_feed`
    activo, en lugar de consumir el feed de las tablas de Batch: evita acoplar
    los bundles y permite ejercitar `UPDATE` y `DELETE`, que en unas ventas
    solo ingeridas apenas se darían.
  - Generador de pedidos con ciclo de vida (`nuevo` → `pagado` → `enviado` →
    `entregado`, con salida a `cancelado`), de modo que los `UPDATE` mueven
    pedidos entre grupos del agregado.
  - Propagación incremental: se lee el feed desde la última versión procesada,
    se deducen los estados obsoletos y se recalculan solo esos.
  - Tabla de control `gold_tfm.cdf.cdf_control` con el puntero de versiones.
    Es lo que hace incremental el proceso: sin ella habría que releer el feed
    completo en cada ejecución.
  - Cubiertos los dos errores clásicos del procesamiento incremental: ignorar
    las preimágenes de los `UPDATE` (deja el grupo de origen inflado para
    siempre) y no borrar los grupos que se quedan sin filas (un `MERGE` nunca
    los toca y quedan congelados con un valor falso).
  - Se recalcula por grupo afectado en vez de acumular deltas: converge sola
    ante un reproceso, en lugar de duplicar importes de forma silenciosa.
  - Eliminadas del caso las tareas `ingest_bronze` y `promote_silver` que
    venían del scaffold: aquí no hay landing zone.
  - El arranque en frío calcula el agregado completo en vez de leer el feed
    desde la versión 0. Además de ser lo conceptualmente correcto —el feed
    propaga cambios sobre un estado, no lo construye—, leer desde la versión 0
    atraviesa la creación de la tabla y Delta lo rechaza con
    `DELTA_CHANGE_DATA_FEED_INCOMPATIBLE_DATA_SCHEMA`.
  - Las altas del generador se aplican con `upsert` y no con `append`: los
    `pedido_id` se derivan de la semilla, así que repetir un lote con `append`
    duplicaba la clave primaria en la tabla origen.
  - El parámetro `lote` pasa a valer 0 por defecto, lo que deriva la semilla de
    la versión actual de la tabla: cada ejecución produce cambios distintos sin
    tener que pasar nada. Un valor explícito sigue haciendo el lote
    reproducible, y ahora además idempotente.
  - Dashboard AI/BI del caso, con el puntero de versiones y la marca de
    recálculo por estado, que es lo que hace visible qué tocó cada ejecución.
  - 15 tests en verde.
