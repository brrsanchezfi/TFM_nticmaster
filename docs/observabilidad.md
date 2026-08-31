# Observabilidad

Dos mecanismos distintos, con propósitos que conviene no mezclar: uno para
depurar cuando algo falla, otro para responder preguntas sobre cómo va la
plataforma.

## Registro de ejecuciones — la tabla de control

`IngestionOpsLogger` de DKOps escribe una **tabla Delta** con una fila por
evento del ciclo de vida de cada ingesta:

| Columna | Contenido |
|---|---|
| `run_id` | Identificador de la ejecución |
| `pipeline` | Caso de uso que la lanzó |
| `dataset` | Dataset ingerido |
| `status` | `STARTED`, `SUCCESS` o `FAILED` |
| `rows_read`, `rows_written` | Volumen procesado |
| `started_at`, `finished_at` | Marcas temporales |
| `notes` | Detalle libre; en los fallos, el error |

Los cuatro casos de uso escriben en **la misma tabla**:

    abfss://landing@lakehousedkops.dfs.core.windows.net/tfm/_ops/ingestas

DKOps la crea por ruta, no registrada en el catálogo. Para poder consultarla
con un nombre limpio se registra como tabla externa:

```sql
CREATE SCHEMA IF NOT EXISTS gold_tfm.ops;

CREATE TABLE IF NOT EXISTS gold_tfm.ops.ingestas
USING DELTA
LOCATION 'abfss://landing@lakehousedkops.dfs.core.windows.net/tfm/_ops/ingestas';
```

La columna `pipeline` distingue el origen, así que una sola tabla sirve para
los cuatro casos. Eso es lo que permite un tablero único en lugar de cuatro.

### Qué se puede preguntar

Estas son las consultas para las que se diseñó la tabla. **Hoy devuelven cero**
por la incidencia que se describe más abajo: solo se registran los inicios.

```sql
-- Tasa de éxito por caso de uso
SELECT pipeline,
       COUNT_IF(status = 'SUCCESS') AS ok,
       COUNT_IF(status = 'FAILED')  AS fallidas
FROM gold_tfm.ops.ingestas
GROUP BY pipeline;

-- Duración media de cada dataset
SELECT dataset,
       AVG(UNIX_TIMESTAMP(finished_at) - UNIX_TIMESTAMP(started_at)) AS segundos
FROM gold_tfm.ops.ingestas
WHERE status = 'SUCCESS'
GROUP BY dataset;

-- Últimos fallos con su causa
SELECT started_at, pipeline, dataset, notes
FROM gold_tfm.ops.ingestas
WHERE status = 'FAILED'
ORDER BY started_at DESC;
```

## Log de aplicación — la traza de texto

`AppLogger` escribe la traza de ejecución en fichero, con rotación a 10 MB y
retención de 7 días. Se configura con `LOG_DIR` en el `config.json` de cada
caso, segmentado por caso de uso, y el nombre del fichero lo da el subproceso:

    LOG_DIR = abfss://landing@lakehousedkops.dfs.core.windows.net/tfm/_logs/<caso>

    tfm/_logs/
    ├── batch/      ingest_bronze.log, promote_silver.log, build_gold.log
    ├── streaming/  poll_api.log, ingest_bronze.log, promote_silver.log, build_gold.log
    ├── cdc/        simulate_source.log, ingest_bronze.log, promote_silver.log, build_gold.log
    └── cdf/        simulate_changes.log, propagate_cdf.log

Así se puede seguir una tarea concreta sin bucear en la traza de todo el
pipeline.

### Por qué no un volumen de Unity Catalog

La primera versión apuntaba `LOG_DIR` a un volumen, con el razonamiento de que
un log es un fichero de texto y un volumen lo expone por POSIX. **Era un
error**, y costó descubrirlo:

Los volúmenes exponen el almacenamiento por FUSE, donde **no se admite añadir a
un fichero que ya existe**: crear y sobrescribir sí, escritura posicional no.
`AppLogger` abre el log en modo append con rotación, de modo que la primera
ejecución creaba el fichero sin problema y **la segunda se quedaba bloqueada
indefinidamente**, sin error ni traza — el proceso moría en el minuto de
espera del job.

El síntoma era desconcertante: el log de la tarea tenía siete líneas y se
cortaba justo después de anunciar que el manejador de fichero estaba activo.

DKOps distingue el tipo de ruta en `add_file_handler` y usa un manejador
distinto para URIs de nube, así que basta con declarar `LOG_DIR` como
`abfss://`. Verificado ejecutando el mismo caso dos veces seguidas, que es lo
que fallaba antes.

Los volúmenes siguen siendo la herramienta correcta para **subir y leer**
ficheros —la landing zone de batch y CDC—, pero no para ficheros que un
proceso reabre y amplía.

## Por qué el tablero se construye sobre la tabla y no sobre el texto

Es la distinción que ordena todo lo anterior. El log de texto está pensado para
que una persona lea qué pasó en una ejecución concreta; no se consulta con SQL
ni se agrega. La tabla de control es estructurada y responde preguntas
transversales: cuántas ejecuciones fallaron esta semana, qué dataset tarda más,
cuándo empezó a degradarse un pipeline.

Dicho de otro modo: el texto sirve para **diagnosticar un caso**, la tabla para
**vigilar el conjunto**.

## Un tercer registro que no se gestiona aquí

Databricks conserva por su cuenta el `stdout` y `stderr` del driver, accesible
desde la interfaz de cada ejecución. Es donde aparecen las trazas completas de
Spark, y fue lo que permitió diagnosticar varios fallos durante el desarrollo.

Se retiene 30 días y después se pierde. Conservarlo más tiempo exigiría
configurar `cluster_log_conf` en los jobs, que no se ha hecho: para el alcance
del TFM, la tabla de control cubre la necesidad de histórico.

## Limitaciones conocidas

### La tabla solo registra inicios

Contiene 25 filas, **todas `STARTED`**: 13 de `retail_sales`, 7 de
`weather_events` y 5 de `customers`. Ni una `SUCCESS` ni una `FAILED`, y
`finished_at` siempre a NULL.

La causa está en `ops_logger.py` de DKOps. El esquema declara `started_at` como
`nullable=False`, pero `log_success` y `log_failure` construyen su fila sin ese
campo —lo cual tiene sentido, porque un cierre no reabre el inicio—, así que
`createDataFrame` aborta con `[CANNOT_BE_NONE]`. El error se captura en un
`except` que solo emite un *warning*, de modo que **el fallo es silencioso**: la
ingesta termina bien y nadie se entera de que el cierre no se ha registrado.

Reproducido en local, sin Databricks: la fila `STARTED` pasa y la `SUCCESS`
lanza la excepción.

Mientras no se corrija, la tabla responde **qué se lanzó y cuándo**, pero no si
terminó bien ni cuántas filas escribió. Es lo que falta para el tablero.

### CDF no se registra

El caso **CDF no aparece** en la tabla de control. Su pipeline no construye un
`IngestionEngine` —lee un Change Data Feed en lugar de ingerir desde una
landing zone—, así que no instancia el registro de operaciones. Instrumentarlo
exigiría añadir las llamadas a mano en sus entrypoints.
