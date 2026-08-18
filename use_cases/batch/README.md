# Caso de uso: batch (retail_sales)

Pipeline Landing → Bronze → Silver → Gold sobre ventas retail sintéticas.
Es el caso piloto del TFM: el que valida la cadena completa con la mínima
complejidad posible.

La explicación de diseño y las decisiones de modelado están en
[`docs/casos_uso/batch.md`](../../docs/casos_uso/batch.md). Este README es
operativo: cómo ejecutarlo.

## Qué hay aquí

    contracts/
      ingestion/bronze/ventas.json   Landing -> Bronze  (load_type: full)
      ingestion/silver/ventas.json   Bronze  -> Silver  (strategy: full_merge)
      tables/{bronze,silver,gold}/   Esquema y gobierno de las tres tablas
    dashboards/
      ventas_kpis.lvdash.json        Dashboard AI/BI de consumo
    src/retail_sales/
      pipeline.py                    Cableado de DKOps (única fontanería)
      jobs/                          Entrypoints de las tres tareas
      transformations/gold_metrics.py  Lógica de negocio del dominio
      generators/generate_sales.py   Generador de datos sintéticos

## Desarrollo local (offline)

    cd use_cases/batch
    pip install -e ".[local]"
    pytest tests/unit -v

Los tests no necesitan Databricks ni Unity Catalog: los del generador son
Python puro y los de `compute_kpis` levantan un Spark local.

## Generar datos y subirlos a la landing

    python -m retail_sales.generators.generate_sales --out /tmp/ventas --rows 500

    databricks fs mkdir dbfs:/Volumes/bronze_tfm/batch/landing/ventas
    databricks fs cp /tmp/ventas/<fichero>.json \
      dbfs:/Volumes/bronze_tfm/batch/landing/ventas/

La subida va por un **volumen externo de Unity Catalog**, no por `az storage`:
el acceso al lake se hace con la identidad del access connector, no con la
personal.

Para generar un lote distinto, cambia `--semilla`. Con la misma semilla el
dataset es idéntico, lo que permite reproducir una ejecución exacta.

## Desplegar y ejecutar

    databricks bundle validate -t dev
    databricks bundle deploy -t dev
    databricks bundle run retail_sales_pipeline -t dev

El despliegue construye el wheel invocando `python -m build`, así que hay que
lanzarlo desde un entorno que tenga ese paquete instalado. Ejecutarlo desde la
extensión de VS Code conectada a un cluster falla con `No module named build`,
porque usa el Python del cluster.

El job encadena `ingest_bronze` → `promote_silver` → `build_gold` sobre un
único job cluster single-node que se apaga al terminar.

## Resultado esperado

| Capa | Filas | Por qué |
|---|---|---|
| Bronze | 525 | 500 ventas + 25 reemisiones |
| Silver | 500 | `full_merge` deduplica por `venta_id` |
| Gold | 249 | Agregados por fecha × categoría × canal |

Reejecutar el pipeline el mismo día no duplica datos: Bronze sobreescribe la
partición `_ingested_date` del día y Gold se reconstruye entera.

## Consumo

El dashboard se despliega con el propio bundle. Su URL aparece en:

    databricks bundle summary -t dev

## Limitaciones conocidas

- El contrato de Silver no puede declarar `_silver_created_at`: la estrategia
  `full_merge` de DKOps no la genera. Reportado en el repositorio de DKOps.
- Gold se reconstruye completa en cada ejecución. Con volúmenes reales habría
  que pasar a un `upsert` por fecha.
- El job cluster es single-node, así que no hay ahorro por instancias spot:
  Azure exige que el driver sea on-demand.
