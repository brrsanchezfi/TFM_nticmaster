# Estado del proyecto

Última actualización: 5 de septiembre de 2026.

## Roadmap

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Diseño | Hecho |
| 1 | Scaffolding del repositorio | Hecho |
| 2 | Catálogos y schemas en el workspace | Hecho, desplegado por API |
| 3 | Dependencia de ingesta y los 4 bundles | Hecho |
| 4 | Caso de uso Batch | Hecho, ejecutado end-to-end |
| 5 | Caso de uso CDF | Hecho, ejecutado end-to-end |
| 6 | Caso de uso CDC | Hecho, ejecutado end-to-end |
| 7 | Caso de uso Streaming | Hecho, ejecutado end-to-end |
| 8 | Tablas externas y observabilidad centralizada | Hecho |
| 9 | Ejecución y pruebas en local | Hecho |
| 10 | Modelo dimensional en Batch | Hecho |
| 11 | Despliegue con Asset Bundles | En curso, manual |
| 12 | Documentación final | En curso |
| 13 | Revisión y defensa | Pendiente |

## Lo que funciona hoy

**Los cuatro casos de uso** están desplegados y ejecutados en Databricks, cada
uno con su dashboard de consumo: 4 jobs, 4 dashboards y 18 tablas repartidas en
los tres catálogos.

| Caso | Estrategia | Bronze | Silver | Gold |
|---|---|---|---|---|
| Batch | `full_merge` | 525 | 500 | 249 |
| Streaming | `append_dedup` | 15 | 15 | 15 |
| CDC | `cdc_merge` | 1360 | 240 | 15 |
| CDF | (ninguna) | (sin Bronze) | 310 | 3 |

En Batch, las 525 filas de Bronze colapsan a 500 en Silver: son las 25
reemisiones que el generador introduce a propósito para que `full_merge` tenga
algo que resolver. En CDC, 1360 eventos acumulados producen 240 clientes
vigentes.

El contraste entre las tres estrategias de promoción es uno de los resultados
más ilustrativos del trabajo: **las tres son una línea distinta en un fichero
JSON**, y el código de los cuatro casos es el mismo.

### Gobierno de las tablas

Las **18 de 18** tablas son `EXTERNAL` y su ubicación reproduce su nombre
lógico:

    abfss://<capa>@lakehousedkops.dfs.core.windows.net/<catálogo>/<esquema>/<tabla>

Antes quedaban gestionadas bajo `__unitystorage/catalogs/<uuid>/`, ilegible y
sin relación con el nombre de la tabla. Las 18 llevan comentario de tabla. Las
únicas columnas sin documentar son `_rescued_data`, que la genera Spark al leer
JSON y no está en ningún contrato, y `_silver_created_at`, que es la novena
incidencia abierta.

### Observabilidad

Dos mecanismos, descritos en [observabilidad.md](observabilidad.md): una tabla
Delta de control común a los cuatro casos (la columna `pipeline` los distingue)
y un log de texto por caso de uso y subproceso en
`abfss://.../tfm/_logs/<caso>/<subproceso>.log`.

Los cuatro casos están desplegados con v0.3.5. La tabla de control registra
aperturas y cierres de los tres pipelines que construyen un `IngestionEngine`:

| Pipeline | STARTED | SUCCESS |
|---|---|---|
| `retail_sales` | 15 | 2 |
| `weather_events` | 9 | 2 |
| `customers` | 7 | 2 |

El desequilibrio entre columnas es histórico: las filas anteriores a v0.3.4
quedaron sin su cierre y no se han borrado, porque documentan el fallo.

Los logs se escriben por tramos desde v0.3.5, con un token por ejecución. Antes
se reescribía el fichero entero en cada sincronización y un fallo puntual se
llevaba el histórico: es la octava incidencia, detallada más abajo.

## Criterios de éxito

Del núcleo evaluable, **7 de 8**:

- Cumplido: Cada caso ejecuta su pipeline completo sin intervención manual
- Cumplido: Los 4 Asset Bundles se validan y despliegan de forma independiente
- Cumplido: CDC captura y procesa INSERT/UPDATE/DELETE
- Cumplido: Streaming ingiere desde una API pública
- Cumplido: CDF demuestra procesamiento incremental
- Cumplido: Unity Catalog organiza catálogos, schemas y tablas por capa y caso
- Pendiente: Documentación completa y navegable sin leer código
- Cumplido: Diagramas versionados en Mermaid

## Incidencias reportadas a DKOps

Nueve detectadas durante la implementación, **ocho corregidas**:

| # | Incidencia | Corregida en |
|---|---|---|
| 1 | `add_silver_timestamps` no generaba `_silver_created_at` | v0.3.1 |
| 2 | El tag `v0.3.0` producía un wheel identificado como `0.2.4` | v0.3.1 |
| 3 | Los comentarios del contrato solo llegaban a Unity Catalog vía `CreateWriter` | v0.3.1 |
| 4 | `cdc_merge` dejaba `is_deleted` a NULL si la columna venía en el DataFrame | v0.3.3 |
| 5 | `license = "MIT"` (PEP 639) exigía `setuptools>=77` con `build-system` en `>=68` | v0.3.2 |
| 6 | Solo `CreateWriter` respetaba `type: EXTERNAL` y `location` del contrato | v0.3.3 |
| 7 | `log_success` y `log_failure` no escriben nunca en la tabla de control | v0.3.4 |
| 8 | Cada sync reescribía el log entero, así que un fallo lo dejaba a 0 bytes | v0.3.5 |
| 9 | `_silver_created_at` no recibe el comentario del contrato | pendiente |

La quinta es la más instructiva: se introdujo **al corregir las tres primeras**
y solo se manifestaba en el cluster, no en un entorno de desarrollo. Ninguna
tarea llegaba a arrancar.

### La séptima, en detalle

Durante 25 ejecuciones la tabla de control solo acumuló filas `STARTED`, con
`finished_at` a NULL: ninguna `SUCCESS` ni `FAILED`.

La causa estaba en `ops_logger.py`. El esquema declaraba `started_at` como
`nullable=False`, pero `log_success` y `log_failure` construyen su fila sin ese
campo (un cierre no reabre el inicio), de modo que `createDataFrame` abortaba
con `[CANNOT_BE_NONE]`. El error lo capturaba un `except` que solo emitía un
*warning*, así que **el fallo era silencioso**: la ingesta terminaba en verde y
nadie se enteraba de que el cierre no se había registrado.

Se reprodujo en local con `createDataFrame` a secas, sin Databricks: la fila
`STARTED` pasaba y la `SUCCESS` lanzaba la excepción. Eso descartó que fuera
cosa del entorno.

Corregido en v0.3.4, que adopta las tres correcciones propuestas: `started_at`
pasa a nullable, el logger lo recuerda por `run_id` y lo repite en el cierre
(de modo que la duración sale de una resta y no de un self-join) y el `except`
sube de `warning` a `error` con el tipo de excepción. Se añadió además el test
de integración que faltaba: los de mocks pasaban en verde porque
`createDataFrame` sobre un `MagicMock` nunca falla.

Verificado en Databricks tras actualizar: `SUCCESS | rows_written=525`, con las
duraciones ya calculables desde la propia fila.

### La octava, en detalle

De 13 ficheros de log, 5 quedaron a 0 bytes, con la tarea terminando en
`SUCCESS` y su stdout mostrando cuatro escrituras correctas.

Comparar las cuatro tareas de una misma ejecución aisló la variable: en tres, el
fichero medía exactamente lo que escribió la última sincronización; en la cuarta,
esa sincronización fue **lo último que hizo el proceso**. `dbutils.fs.put` con
`overwrite=True` trunca el destino antes de volcar y devuelve el control antes
de confirmar el blob, así que morir en esa ventana deja el fichero vacío.

Lo grave no era la carrera, que no depende de DKOps, sino que **cada
sincronización reescribía el fichero entero**: no se perdía el último tramo, se
perdía el histórico completo.

Corregido en v0.3.5, que escribe un objeto por tramo y no vuelve a tocarlo,
reintenta el tramo que falla y avisa por stdout si el log queda incompleto.

## Fallos que solo aparecieron al ejecutar

Merecen su sitio en la memoria, porque ninguno lo habrían detectado los tests:

- **`EXECUTION_ENVIRONMENT` debe ser `local`** dentro de un job cluster, y el
  entorno se resuelve por `workspace_id`, no por nombre.
- **`first_on_demand` debe ser >= 1**: en single-node la única VM es el driver
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
datos (una fila por evento con `op_type` y `op_ts`), de modo que el pipeline es
idéntico al que procesaría Change Tracking.

**Sin App Registrations en Entra ID.** Impide automatizar el despliegue con
una identidad propia. El despliegue se hace con la sesión del usuario.

## Deuda técnica

- CDF no aparece en la tabla de control: su pipeline no construye un
  `IngestionEngine`, así que no instancia el registro de operaciones.
- El despliegue se hace a mano con `databricks bundle deploy`. Automatizarlo
  requeriría un service principal, y no hay permisos para crear App
  Registrations en Entra ID.
- 7 páginas de `docs/` pendientes de redactar: arquitectura (3), stack, costes,
  CI/CD y conclusiones.
- Las rutas con formato `lote=...` hacen que Spark infiera una columna de
  partición no declarada en el contrato (`lote` en la Bronze de streaming).
- Gold se reconstruye completa en los cuatro casos. Con volúmenes reales
  habría que pasar a upserts incrementales.
