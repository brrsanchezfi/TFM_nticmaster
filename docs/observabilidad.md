# Observabilidad

Hay dos registros. La tabla de control sirve para consultar el conjunto de
ejecuciones con SQL. Los logs de texto sirven para revisar una ejecución
concreta.

## Tabla de control

`IngestionOpsLogger` de DKOps escribe una fila por evento del ciclo de vida de
cada ingesta.

| Columna | Contenido |
|---|---|
| `run_id` | Identificador de la ejecución |
| `pipeline` | Caso de uso |
| `dataset` | Dataset ingerido |
| `status` | `STARTED`, `SUCCESS` o `FAILED` |
| `rows_read`, `rows_written` | Filas leídas y escritas |
| `started_at`, `finished_at` | Inicio y fin |
| `notes` | Detalle libre; en los fallos, el error |

Los casos batch, streaming y CDC escriben en la misma tabla Delta, en la
landing:

    abfss://landing@<cuenta>.dfs.core.windows.net/tfm/_ops/ingestas

DKOps la crea por ruta, sin registrarla en el catálogo. Para consultarla por
nombre hay que registrarla una vez:

```sql
CREATE SCHEMA IF NOT EXISTS gold_tfm.ops;

CREATE TABLE IF NOT EXISTS gold_tfm.ops.ingestas
USING DELTA
LOCATION 'abfss://landing@<cuenta>.dfs.core.windows.net/tfm/_ops/ingestas';
```

Consultas de ejemplo:

```sql
-- Ejecuciones correctas y fallidas por caso
SELECT pipeline,
       COUNT_IF(status = 'SUCCESS') AS ok,
       COUNT_IF(status = 'FAILED')  AS fallidas
FROM gold_tfm.ops.ingestas
GROUP BY pipeline;

-- Duración media por dataset, en segundos
SELECT dataset,
       AVG(UNIX_TIMESTAMP(finished_at) - UNIX_TIMESTAMP(started_at)) AS segundos
FROM gold_tfm.ops.ingestas
WHERE status = 'SUCCESS'
GROUP BY dataset;

-- Últimos fallos
SELECT started_at, pipeline, dataset, notes
FROM gold_tfm.ops.ingestas
WHERE status = 'FAILED'
ORDER BY started_at DESC;
```

Hay más filas `STARTED` que `SUCCESS` porque las ejecuciones anteriores a
DKOps v0.3.4 no registraban el cierre. No se han borrado.

CDF no escribe en esta tabla: no construye un `IngestionEngine`, que es quien
crea el registro.

## Logs de texto

`AppLogger` escribe un log por caso y por subproceso. La carpeta se configura
con `LOG_DIR` en el `config.dev.json` de cada caso:

    abfss://landing@<cuenta>.dfs.core.windows.net/tfm/_logs/<caso>

| Caso | Subprocesos |
|---|---|
| batch | `ingest_bronze_dimensiones`, `ingest_bronze_ventas`, `promote_silver_dimensiones`, `promote_silver_ventas`, `build_gold` |
| streaming | `poll_api`, `ingest_bronze`, `promote_silver`, `build_gold` |
| cdc | `simulate_source`, `ingest_bronze`, `promote_silver`, `build_gold` |
| cdf | `simulate_changes`, `propagate_cdf` |

Desde DKOps v0.3.5 cada sincronización escribe un fichero nuevo:

    ingest_bronze.20260906T023042Z-a3f1c9.0001.log
    ingest_bronze.20260906T023042Z-a3f1c9.0002.log

La parte central identifica la ejecución. El log completo se reconstruye con
`AppLogger.read_cloud_log(spark, log_dir, "ingest_bronze")`.

`LOG_DIR` tiene que ser una ruta `abfss://` y no un volumen. Los volúmenes no
admiten añadir a un fichero existente, y con los logs en un volumen la segunda
ejecución de un caso se quedaba bloqueada sin error.

## Salida del driver

Databricks guarda el `stdout` y el `stderr` del driver de cada ejecución durante
30 días. Ahí están las trazas completas de Spark. Para conservarlas más tiempo
habría que configurar `cluster_log_conf` en los jobs, cosa que no se ha hecho.

## Incidencias corregidas

**Cierres sin registrar (DKOps v0.3.4).** Durante 25 ejecuciones la tabla solo
recibió filas `STARTED`. El esquema declaraba `started_at` como no nulo, pero
`log_success` y `log_failure` construían su fila sin ese campo, y
`createDataFrame` fallaba con `[CANNOT_BE_NONE]`. Un `except` convertía el error
en un aviso, así que la ingesta terminaba bien sin registrar el cierre. Desde
v0.3.4 el logger guarda `started_at` por `run_id` y lo repite en la fila de
cierre, y el error se registra como `error`.

**Logs vacíos (DKOps v0.3.5).** De 13 ficheros de log, 5 quedaron a 0 bytes con
la tarea terminada en `SUCCESS`. `dbutils.fs.put` con `overwrite=True` vacía el
destino antes de escribir, y cada sincronización reescribía el fichero entero.
Si el proceso terminaba justo en esa escritura, se perdía todo el log. Desde
v0.3.5 cada tramo va a un fichero propio, se reintenta si falla y se avisa por
`stdout` si el log queda incompleto.
