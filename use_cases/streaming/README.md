# Caso de uso: streaming (weather_events)

Ingesta incremental con Auto Loader desde una API pública, sin Kafka ni Event
Hubs. Un job corto deposita eventos en la landing y Auto Loader los consume.

El diseño está en [`docs/casos_uso/streaming.md`](../../docs/casos_uso/streaming.md).
Este README es operativo.

## Qué hay aquí

    contracts/
      ingestion/bronze/eventos.json  Auto Loader, trigger availableNow
      ingestion/silver/eventos.json  append_dedup por ciudad + hora
      tables/{bronze,silver,gold}/   Esquema y gobierno de las tres tablas
    dashboards/
      eventos_meteo.lvdash.json      Dashboard AI/BI de consumo
    src/weather_events/
      producer/poll_api.py           Cliente de la API (sin Spark)
      jobs/poll_api.py               Deja el lote en la landing
      jobs/{ingest_bronze,promote_silver,build_gold}.py
      transformations/gold_metrics.py  Agregación por ventana horaria

## Desarrollo local (offline)

    cd use_cases/streaming
    pip install -e ".[local]"
    pytest tests/unit -v

Los tests del productor simulan la respuesta de la API: no necesitan red.

Para ver qué devuelve la API de verdad:

    python -c "from weather_events.producer.poll_api import consultar_ciudad; \
      print(consultar_ciudad('Madrid', 40.4168, -3.7038))"

## Desplegar y ejecutar

    databricks bundle validate -t dev
    databricks bundle deploy -t dev
    databricks bundle run weather_events_pipeline -t dev

Cuatro tareas encadenadas: `poll_api` → `ingest_bronze` → `promote_silver` →
`build_gold`, sobre un único job cluster.

## Qué esperar entre ejecuciones

Este es el comportamiento a observar, y no es intuitivo:

| | Bronze | Silver |
|---|---|---|
| Cada ejecución | **+5 filas** (una por ciudad) | **+0** si la API no ha publicado nada nuevo |
| Cuando la API renueva | +5 filas | +5 filas |

Bronze crece siempre porque cada lote es un fichero nuevo. Silver solo crece
cuando hay observaciones nuevas: la API devuelve la misma lectura hasta que
publica otra, y `append_dedup` descarta las repetidas por `ciudad` + `hora`.

Si Bronze y Silver crecen igual en cada pasada, algo va mal en la
deduplicación.

## Ingesta continua

El job trae un `schedule` cada 15 minutos, **en pausa** para no consumir DBUs.
Activarlo desde la UI del job convierte el caso en una ingesta continua real.

## Limitaciones conocidas

- Auto Loader guarda su estado en las rutas `checkpoint` y `schemas` de
  `config.dev.json`. Si se borran, la siguiente ejecución reingiere toda la
  landing y duplica Bronze.
- Gold se reconstruye entera en cada ejecución. Con volúmenes reales habría que
  pasar a un `upsert` por ventana.
- La API tiene límite de uso gratuito. Con cinco ciudades cada 15 minutos queda
  muy por debajo, pero subir mucho la frecuencia o el número de ciudades podría
  provocar respuestas con error.
