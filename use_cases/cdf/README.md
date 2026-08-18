# Caso de uso: CDF (orders)

Propagación incremental de cambios a Gold usando el Change Data Feed de Delta
Lake. A diferencia de los otros casos, aquí **no hay ingesta desde una landing
zone**: el origen es una tabla Delta que ya vive en Silver.

El diseño y las decisiones están en
[`docs/casos_uso/cdf.md`](../../docs/casos_uso/cdf.md). Este README es
operativo.

## Qué hay aquí

    contracts/tables/
      silver/pedidos.json            Tabla origen, con change_data_feed: true
      gold/pedidos_agregado.json     Agregado por estado
      gold/cdf_control.json          Puntero de versiones ya procesadas
    src/orders/
      pipeline.py                    Launcher + carga de contratos
      jobs/simulate_changes.py       Aplica altas, updates y bajas al origen
      jobs/propagate_cdf.py          Lee el feed y propaga solo lo afectado
      transformations/cdf_metrics.py Lógica de propagación (funciones puras)
      generators/generate_orders.py  Generador de pedidos y lotes de cambios

## Por qué no hay ingest_bronze ni promote_silver

El scaffold inicial asumía la estructura Landing → Bronze → Silver → Gold de
los otros casos. Aquí no aplica: el punto de partida es una tabla Delta, no un
fichero. Las dos tareas del job son mutar el origen y propagar sus cambios.

## Desarrollo local (offline)

    cd use_cases/cdf
    pip install -e ".[local]"
    pytest tests/unit -v

Los tests no necesitan Databricks. Cubren los dos errores clásicos del
procesamiento incremental —ignorar las preimágenes de los `UPDATE` y dejar
huérfanos los grupos que se quedan vacíos— además del ciclo de vida del
generador.

## Desplegar y ejecutar

    databricks bundle validate -t dev
    databricks bundle deploy -t dev

Primera ejecución, que siembra la tabla origen con 300 pedidos:

    databricks bundle run orders_cdf_pipeline -t dev

Ejecuciones siguientes: cada una aplica un lote distinto de cambios sin que
haya que pasar nada.

    databricks bundle run orders_cdf_pipeline -t dev
    databricks bundle run orders_cdf_pipeline -t dev
    databricks bundle run orders_cdf_pipeline -t dev

Cada pasada aplica 20 altas, 30 cambios de estado y 10 bajas —60 operaciones,
saldo neto +10 pedidos— y el puntero avanza. Encadenar varias es la forma de
ver el mecanismo en funcionamiento.

### El parámetro `lote`

Controla la semilla del generador y tiene dos modos:

| Valor | Comportamiento |
|---|---|
| `0` (por defecto) | La semilla se deriva de la versión actual de la tabla, así que **cada ejecución genera cambios distintos** |
| Explícito (`lote=7`) | Semilla fija: el lote es siempre el mismo y la ejecución reproducible |

    databricks bundle run orders_cdf_pipeline -t dev --params lote=7

Repetir un lote explícito es **idempotente**: las altas se aplican con `upsert`
sobre `pedido_id`, no con `append`. Con `append`, repetir el mismo lote
insertaría de nuevo los mismos identificadores y duplicaría la clave primaria,
porque los `pedido_id` se generan de forma determinista a partir de la semilla.

## Cómo comprobar que es incremental

Después de un par de ejecuciones:

```sql
-- Hasta qué versión se ha propagado
SELECT * FROM gold_tfm.cdf.cdf_control;

-- Qué estados se recalcularon en la última pasada y cuáles no se tocaron
SELECT estado, num_pedidos, _recalculado_at
FROM gold_tfm.cdf.pedidos_agregado
ORDER BY _recalculado_at DESC;

-- El feed en crudo, para ver los cuatro tipos de cambio
SELECT _change_type, COUNT(*)
FROM table_changes('silver_tfm.cdf.pedidos', 1)
GROUP BY _change_type;
```

La columna `_recalculado_at` es la prueba: los estados que el feed no reportó
conservan la marca de tiempo de una ejecución anterior, porque nadie los tocó.

## Limitaciones conocidas

- El agregado se recalcula por grupo afectado, no aplicando deltas. Es algo más
  costoso, pero tolera reprocesos sin descuadrarse.
- El generador lee la tabla origen entera para construir el lote de cambios.
  Con volúmenes reales habría que muestrear en lugar de traerlo todo al driver.
- La retención del Change Data Feed depende de `delta.logRetentionDuration`
  (30 días por defecto). Si una ejecución se retrasa más que eso, el puntero
  apuntaría a una versión ya purgada y habría que reconstruir el agregado
  completo.
