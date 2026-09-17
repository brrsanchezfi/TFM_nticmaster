# Estado del proyecto

Última actualización: 16 de septiembre de 2026.

## Fases

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Diseño | Hecho |
| 1 | Estructura del repositorio | Hecho |
| 2 | Catálogos y esquemas en el workspace | Hecho, creados por API |
| 3 | DKOps como dependencia y los cuatro bundles | Hecho |
| 4 | Caso batch | Hecho |
| 5 | Caso CDF | Hecho |
| 6 | Caso CDC | Hecho |
| 7 | Caso streaming | Hecho |
| 8 | Tablas externas y tabla de control común | Hecho |
| 9 | Ejecución y pruebas en local | Hecho |
| 10 | Modelo dimensional en batch | Hecho |
| 11 | Documentación | Hecho |
| 12 | Memoria y defensa | En curso |

## Cifras

Los cuatro casos están desplegados y ejecutados en Databricks: cuatro jobs,
cuatro dashboards, tres catálogos, trece esquemas y veinticuatro tablas
externas (veintitrés de los casos y la tabla de control).

Filas por capa a 16 de septiembre de 2026. Streaming, CDC y CDF crecen con cada
ejecución, así que estas cifras cambian.

| Caso | Estrategia | Bronze | Silver | Gold |
|---|---|---|---|---|
| Batch | `full_merge` | 525 | 500 | 249 |
| Streaming | `append_dedup` | 35 | 35 | 35 |
| CDC | `cdc_merge` | 1440 | 260 | 15 |
| CDF | recálculo por grupo | sin bronze | 330 | 4 |

En batch, las 525 filas de bronze quedan en 500 en silver: son las 25
reemisiones que introduce el generador. Las cinco dimensiones tienen 4, 6, 8, 12
y 20 filas en silver.

Pruebas unitarias: 36 (batch 13, streaming 7, CDC 7, CDF 9).

## Documentación de las tablas

Todas las tablas llevan el comentario de su contrato. Quedan dos columnas sin
comentario:

- `_rescued_data`, que genera Spark al leer JSON y no está en ningún contrato.
- `_silver_created_at`, que sí lo tiene en el contrato pero no llega al
  catálogo. Es la incidencia 9.

## Incidencias en DKOps

Nueve detectadas durante el trabajo, ocho corregidas.

| # | Incidencia | Corregida en |
|---|---|---|
| 1 | `add_silver_timestamps` no generaba `_silver_created_at` | v0.3.1 |
| 2 | El tag `v0.3.0` producía un wheel con versión `0.2.4` | v0.3.1 |
| 3 | Los comentarios del contrato solo llegaban a Unity Catalog con `CreateWriter` | v0.3.1 |
| 4 | `license = "MIT"` (PEP 639) exigía `setuptools>=77` con `build-system` en `>=68` | v0.3.2 |
| 5 | `cdc_merge` dejaba `is_deleted` a NULL si la columna venía en el DataFrame | v0.3.3 |
| 6 | Solo `CreateWriter` respetaba `type: EXTERNAL` y `location` | v0.3.3 |
| 7 | `log_success` y `log_failure` no escribían en la tabla de control | v0.3.4 |
| 8 | Cada sincronización reescribía el log entero y un fallo lo dejaba vacío | v0.3.5 |
| 9 | `_silver_created_at` no recibe el comentario del contrato | Pendiente |

La 4 apareció al corregir las tres primeras. En local no se notaba, porque pip
construye en un entorno aislado con un setuptools reciente, pero en el cluster
ninguna tarea llegaba a arrancar.

La 7 y la 8 están explicadas en [observabilidad.md](observabilidad.md).

## Fallos de entorno

No los detectaba ninguna prueba unitaria. Aparecieron al ejecutar en Databricks.

- `EXECUTION_ENVIRONMENT` tiene que ser `local` dentro de un job cluster. El
  valor `databricks` significa Databricks Connect desde fuera y exige
  `CLUSTER_ID`.
- Dentro de Databricks, DKOps resuelve el entorno por `workspace_id`, no por
  nombre.
- `first_on_demand` tiene que ser al menos 1 en un cluster de un solo nodo.
- El `checkpoint` y los `schemas` de Auto Loader no pueden estar en `/tmp`: con
  clusters efímeros se pierden y cada ejecución reingiere toda la landing.
- Leer el Change Data Feed desde la versión 0 falla, porque el rango incluye la
  creación de la tabla.
- Los volúmenes de Unity Catalog no admiten añadir a un fichero existente. Con
  los logs en un volumen, la segunda ejecución se bloqueaba sin error.
- Una fuga de columnas internas hasta la landing dejó `is_deleted` a NULL en
  CDC. Cinco ejecuciones terminaron bien con datos incorrectos.

## Bloqueos

- **Proveedor `Microsoft.Sql` sin registrar.** Registrarlo requiere permisos de
  suscripción. El caso CDC usa un simulador que emite el mismo formato que
  Change Tracking: una fila por evento con `op_type` y `op_ts`.
- **Sin App Registrations en Entra ID.** No se puede crear un service principal,
  así que el despliegue se hace con la sesión del usuario y no hay CI/CD.

## Deuda técnica

- CDF no escribe en la tabla de control, porque no construye un
  `IngestionEngine`.
- Gold se reconstruye entera en los cuatro casos.
- Las rutas con `lote=...` hacen que Spark infiera una columna de partición
  `lote` que no está en el contrato de bronze de streaming.
- `scripts/teardown.sh` sigue siendo un marcador y no retira los bundles.
