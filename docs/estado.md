# Estado del proyecto

Última actualización: 30 de agosto de 2026.

## Roadmap

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Diseño | ✅ |
| 1 | Scaffolding del repositorio | ✅ |
| 2 | Terraform (Unity Catalog) | ✅ escrito y validado, **no aplicado** |
| 3 | Catálogos y schemas en el workspace | ✅ desplegado por API |
| 4 | DKOps como dependencia + 4 bundles | ✅ |
| 5 | Caso de uso **Batch** | ✅ ejecutado end-to-end |
| 6 | Caso de uso **CDF** | ✅ ejecutado end-to-end |
| 7 | Caso de uso **CDC** | ✅ ejecutado end-to-end |
| 8 | Caso de uso **Streaming** | ✅ ejecutado end-to-end |
| 8b | Tablas externas y observabilidad centralizada | 🔶 en revisión (PR abierto) |
| 9 | CI/CD (GitHub Actions) | ⬜ workflows vacíos |
| 10 | Documentación final | 🔶 6 de 14 páginas |
| 11 | Revisión y defensa | ⬜ |

## Lo que funciona hoy

**Los cuatro casos de uso** están desplegados y ejecutados en Databricks, cada
uno con su dashboard de consumo: 4 jobs, 4 dashboards y 13 tablas repartidas en
los tres catálogos.

| Caso | Estrategia | Bronze | Silver | Gold |
|---|---|---|---|---|
| Batch | `full_merge` | 525 | 500 | 249 |
| Streaming | `append_dedup` | 10 | 10 | 10 |
| CDC | `cdc_merge` | 1320 | 230 | 15 |
| CDF | — | — | 300 | 1 |

En Batch, las 525 filas de Bronze colapsan a 500 en Silver: son las 25
reemisiones que el generador introduce a propósito para que `full_merge` tenga
algo que resolver. En CDC, 1320 eventos acumulados producen 230 clientes
vigentes.

El contraste entre las tres estrategias de promoción es uno de los resultados
más ilustrativos del trabajo: **las tres son una línea distinta en un fichero
JSON**, y el código de los cuatro casos es el mismo.

### Gobierno de las tablas

Las **13 de 13** tablas son `EXTERNAL` y su ubicación reproduce su nombre
lógico:

    abfss://<capa>@lakehousedkops.dfs.core.windows.net/<catálogo>/<esquema>/<tabla>

Antes quedaban gestionadas bajo `__unitystorage/catalogs/<uuid>/`, ilegible y
sin relación con el nombre de la tabla. Las 13 llevan comentario de tabla, y de
las 118 columnas solo 5 quedan sin documentar: todas autogeneradas
(`_rescued_data`, `lote`).

### Observabilidad

Dos mecanismos, descritos en [observabilidad.md](observabilidad.md): una tabla
Delta de control común a los cuatro casos —la columna `pipeline` los distingue—
y un log de texto por caso de uso y subproceso en
`abfss://…/tfm/_logs/<caso>/<subproceso>.log`.

Los cuatro casos están desplegados con v0.3.4 y ejecutados. La tabla de control
registra ya aperturas y cierres de los tres pipelines que construyen un
`IngestionEngine`:

| Pipeline | STARTED | SUCCESS |
|---|---|---|
| `retail_sales` | 15 | 2 |
| `weather_events` | 9 | 2 |
| `customers` | 7 | 2 |

El desequilibrio entre columnas es histórico: las filas anteriores a v0.3.4
quedaron sin su cierre y no se han borrado, porque documentan el fallo.

Los cuatro directorios de logs existen y están segmentados por subproceso.
**Varios ficheros quedan a 0 bytes**, siempre los de las primeras tareas de cada
job: en `batch` el `ingest_bronze.log` estuvo a 0 tras una ejecución y se llenó
en la siguiente, lo que apunta a que el manejador de nube —que sincroniza con
`dbutils.fs.put` cada 5 mensajes— pierde lo pendiente al terminar el proceso.
Pendiente de confirmar.

## Criterios de éxito

Del núcleo evaluable, **7 de 8**:

- [x] Cada caso ejecuta su pipeline completo sin intervención manual
- [x] Los 4 Asset Bundles se validan y despliegan de forma independiente
- [x] CDC captura y procesa INSERT/UPDATE/DELETE
- [x] Streaming ingiere desde una API pública
- [x] CDF demuestra procesamiento incremental
- [x] Unity Catalog organiza catálogos, schemas y tablas por capa y caso
- [ ] Documentación completa y navegable sin leer código
- [x] Diagramas versionados en Mermaid

## Incidencias reportadas a DKOps

Siete detectadas durante la implementación, **las siete corregidas**:

| # | Incidencia | Corregida en |
|---|---|---|
| 1 | `add_silver_timestamps` no generaba `_silver_created_at` | v0.3.1 |
| 2 | El tag `v0.3.0` producía un wheel identificado como `0.2.4` | v0.3.1 |
| 3 | Los comentarios del contrato solo llegaban a Unity Catalog vía `CreateWriter` | v0.3.1 |
| 4 | `cdc_merge` dejaba `is_deleted` a NULL si la columna venía en el DataFrame | v0.3.3 |
| 5 | `license = "MIT"` (PEP 639) exigía `setuptools>=77` con `build-system` en `>=68` | v0.3.2 |
| 6 | Solo `CreateWriter` respetaba `type: EXTERNAL` y `location` del contrato | v0.3.3 |
| 7 | `log_success` y `log_failure` no escriben nunca en la tabla de control | v0.3.4 |

La quinta es la más instructiva: se introdujo **al corregir las tres primeras**
y solo se manifestaba en el cluster, no en un entorno de desarrollo. Ninguna
tarea llegaba a arrancar.

### La séptima, en detalle

Durante 25 ejecuciones la tabla de control solo acumuló filas `STARTED`, con
`finished_at` a NULL: ninguna `SUCCESS` ni `FAILED`.

La causa estaba en `ops_logger.py`. El esquema declaraba `started_at` como
`nullable=False`, pero `log_success` y `log_failure` construyen su fila sin ese
campo —un cierre no reabre el inicio—, de modo que `createDataFrame` abortaba
con `[CANNOT_BE_NONE]`. El error lo capturaba un `except` que solo emitía un
*warning*, así que **el fallo era silencioso**: la ingesta terminaba en verde y
nadie se enteraba de que el cierre no se había registrado.

Se reprodujo en local con `createDataFrame` a secas, sin Databricks: la fila
`STARTED` pasaba y la `SUCCESS` lanzaba la excepción. Eso descartó que fuera
cosa del entorno.

Corregido en v0.3.4, que adopta las tres correcciones propuestas: `started_at`
pasa a nullable, el logger lo recuerda por `run_id` y lo repite en el cierre
—de modo que la duración sale de una resta y no de un self-join— y el `except`
sube de `warning` a `error` con el tipo de excepción. Se añadió además el test
de integración que faltaba: los de mocks pasaban en verde porque
`createDataFrame` sobre un `MagicMock` nunca falla.

Verificado en Databricks tras actualizar: `SUCCESS | rows_written=525`, con las
duraciones ya calculables desde la propia fila.

## Fallos que solo aparecieron al ejecutar

Merecen su sitio en la memoria, porque ninguno lo habrían detectado los tests:

- **`EXECUTION_ENVIRONMENT` debe ser `local`** dentro de un job cluster, y el
  entorno se resuelve por `workspace_id`, no por nombre.
- **`first_on_demand` debe ser ≥ 1**: en single-node la única VM es el driver
  y Azure exige que sea on-demand. No hay ahorro por spot.
- **`checkpoint` y `schemas` de Auto Loader no pueden vivir en `/tmp`**: con
  clusters efímeros se pierden y cada ejecución reingiere la landing entera.
- **Leer el Change Data Feed desde la versión 0** atraviesa la creación de la
  tabla y Delta lo rechaza. El arranque en frío no debe usar el feed.
- **Una fuga de columnas internas** desde Silver hasta la landing hizo que
  `is_deleted` quedara a NULL, y como `NOT NULL` no es `TRUE`, cinco
  ejecuciones terminaron en verde produciendo datos incorrectos.
- **Los volúmenes de Unity Catalog no admiten añadir a un fichero existente.**
  Con `LOG_DIR` en un volumen, la segunda ejecución de cualquier caso se
  bloqueaba sin error ni traza. La ruta correcta es `abfss://`.

Hay un patrón que se repite en tres de los seis: **el proceso termina en verde y
el resultado es incorrecto**. Es el modo de fallo caro, y el que justifica la
tabla de control.

## Restricciones de Unity Catalog que condicionan el diseño

- `DROP TABLE` sobre una tabla externa **no borra los ficheros**, así que al
  recrearla el `CREATE` choca con los datos huérfanos.
- Un volumen y una tabla externa **no pueden compartir ruta**, en ninguna de las
  dos direcciones.

De ahí el orden obligatorio para reconstruir el entorno, en
[infraestructura.md](infraestructura.md).

## Bloqueos abiertos

**`Microsoft.Sql` sin registrar.** Registrar un resource provider es una
operación de suscripción y la cuenta es Contributor solo del Resource Group.
El caso CDC se resolvió con un origen simulado que emite el mismo contrato de
datos —una fila por evento con `op_type` y `op_ts`—, de modo que el pipeline es
idéntico al que procesaría Change Tracking. El módulo Terraform del Azure SQL
está escrito y validado, listo para `enable_cdc_sql = true`.

**Sin App Registrations en Entra ID.** Afecta al CI/CD con OIDC. Rodeo
previsto: usar un service principal de Databricks.

**State de Terraform vacío.** Los catálogos se crearon por API, así que un
`terraform apply` fallaría con "already exists". Queda decidir entre importar
los recursos o documentar Terraform como demostración de IaC.

## Deuda técnica

- Algunos ficheros de log quedan a 0 bytes, siempre los de las primeras tareas
  de cada job. Sospecha: el manejador de nube sincroniza cada 5 mensajes y no
  vacía lo pendiente al terminar el proceso.
- CDF no aparece en la tabla de control: su pipeline no construye un
  `IngestionEngine`, así que no instancia el registro de operaciones.
- Los 5 workflows de GitHub Actions siguen siendo ficheros de 10 líneas.
- 8 páginas de `docs/` pendientes de redactar: arquitectura (3), stack, costes,
  CI/CD y conclusiones.
- Las rutas con formato `lote=...` hacen que Spark infiera una columna de
  partición no declarada en el contrato (`lote` en la Bronze de streaming).
- Gold se reconstruye completa en los cuatro casos. Con volúmenes reales
  habría que pasar a upserts incrementales.
