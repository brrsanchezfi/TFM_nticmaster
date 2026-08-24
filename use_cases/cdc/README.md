# Caso de uso: CDC (customers)

Captura y aplicación de cambios (`INSERT`/`UPDATE`/`DELETE`) desde un sistema
origen, con soft-delete en Silver.

El diseño está en [`docs/casos_uso/cdc.md`](../../docs/casos_uso/cdc.md). Este
README es operativo.

## El origen es simulado, y por qué

El diseño preveía Change Tracking sobre Azure SQL. No es posible: el provider
`Microsoft.Sql` está `NotRegistered` en la suscripción y registrarlo excede los
permisos disponibles.

En su lugar, `simulate_source` emite el mismo contrato de datos que emitiría
Change Tracking: una fila por evento con `op_type` (`I`/`U`/`D`) y `op_ts`. El
pipeline que los procesa es idéntico en ambos casos.

El módulo Terraform del Azure SQL está listo en `infra/`; se activa con
`enable_cdc_sql = true` cuando el provider esté registrado.

## Qué hay aquí

    contracts/
      ingestion/bronze/clientes.json   load_type: cdc
      ingestion/silver/clientes.json   strategy: cdc_merge, watermark op_ts
      tables/bronze/clientes_raw.json      Histórico de eventos, append-only
      tables/silver/clientes_current.json  Foto actual, con is_deleted
      tables/gold/clientes_activos.json    Cartera por segmento y ciudad
      tables/gold/historico_cambios.json   Actividad diaria por operación
    dashboards/
      clientes_cdc.lvdash.json
    src/customers/
      generators/simulate_changes.py   Emite los eventos (sin Spark)
      jobs/simulate_source.py          Los deja en la landing
      jobs/{ingest_bronze,promote_silver,build_gold}.py
      transformations/gold_metrics.py  Cartera e histórico

## Desarrollo local (offline)

    cd use_cases/cdc
    pip install -e ".[local]"
    pytest tests/unit -v

## Desplegar y ejecutar

    databricks bundle validate -t dev
    databricks bundle deploy -t dev
    databricks bundle run customers_cdc_pipeline -t dev

Cuatro tareas: `simulate_source` → `ingest_bronze` → `promote_silver` →
`build_gold`.

La primera ejecución da de alta 200 clientes. Las siguientes emiten 10 altas,
25 modificaciones y 5 bajas sobre los clientes vigentes.

### El parámetro `lote`

| Valor | Comportamiento |
|---|---|
| `0` (por defecto) | La semilla se deriva del reloj: cada ejecución emite cambios distintos |
| Explícito | Semilla fija, lote reproducible |

    databricks bundle run customers_cdc_pipeline -t dev --params lote=7

## Qué esperar entre ejecuciones

| | Bronze | Silver |
|---|---|---|
| Ejecución 1 | 200 eventos | 200 clientes |
| Cada siguiente | **+40 eventos** | **+10 filas** (las altas) y 5 marcadas como baja |

Bronze crece siempre, porque guarda el histórico completo. Silver solo crece
con las altas: las modificaciones actualizan filas existentes y las bajas las
marcan sin eliminarlas.

Si Silver creciera al mismo ritmo que Bronze, el merge no estaría funcionando.

## Comprobaciones útiles

```sql
-- Un cliente con varios eventos, y su única fila en Silver
SELECT cliente_id, op_type, op_ts, segmento
FROM bronze_tfm.cdc.clientes_raw
WHERE cliente_id = 'CLI-00001' ORDER BY op_ts;

SELECT * FROM silver_tfm.cdc.clientes_current WHERE cliente_id = 'CLI-00001';

-- Las bajas siguen ahí, marcadas
SELECT COUNT(*) FROM silver_tfm.cdc.clientes_current WHERE is_deleted;
```

## Limitaciones conocidas

- `cdc_merge` lee Bronze entero en cada ejecución para quedarse con el último
  evento por cliente. Con volúmenes reales habría que filtrar por
  `_ingested_date` o apoyarse en el Change Data Feed de Bronze.
- Las dos tablas Gold se reconstruyen completas en cada pasada.
- El simulador trae al driver los clientes vigentes para construir el lote.
  Con carteras grandes habría que muestrear.
