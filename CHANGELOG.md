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
