# Ejecución local

Los pipelines no necesitan Databricks para ejecutarse. Salvo Auto Loader, todo
el stack (DKOps, Spark, Delta) funciona en un portátil, y eso permite probar la
capa de ingesta sin levantar un cluster.

## Un entorno por caso de uso

Cada caso es un bundle independiente con su propio `pyproject.toml`, así que
lleva su propio entorno virtual:

```bash
for uc in batch streaming cdc cdf; do
  python3 -m venv ~/.venvs/tfm-$uc
  ~/.venvs/tfm-$uc/bin/pip install -e "use_cases/$uc[local]"
done
```

El extra `[local]` añade `pyspark 3.5.3`, `delta-spark 3.2.0` y `pytest`. En
Databricks no se instala: pyspark lo aporta el runtime del cluster.

**Los entornos van fuera del repositorio.** En WSL, crear un venv bajo
`/mnt/c` tarda decenas de minutos, son miles de ficheros pequeños sobre un
montaje de Windows, frente a un par de minutos en el sistema de ficheros de
Linux.

## La configuración local

Cada caso tiene un `config/config.local.json` junto al de Databricks. Tres
campos son los que hacen que funcione fuera del workspace:

| Campo | Por qué |
|---|---|
| `EXECUTION_ENVIRONMENT: "local"` | Levanta una SparkSession normal en vez de Databricks Connect |
| `DATABRICKS_TARGET: "local"` | Sin `workspace_id` que detectar, el ambiente se resuelve por nombre |
| `SPARK_WAREHOUSE_DIR` | Dónde deja Spark las tablas registradas |

Los `paths` apuntan a `/tmp/<caso>/` en lugar de a `abfss://`, y los catálogos
pierden el sufijo `_tfm`: en local no hay Unity Catalog, así que DKOps registra
las tablas con nombre de dos partes (`batch.ventas`) en el catálogo de sesión y
resuelve la ruta física dentro del warehouse.

## Qué se puede ejecutar y qué no

| | Local | Databricks |
|---|---|---|
| Generadores y simuladores | si | si |
| Ingesta a Bronze (batch, cdc) | si | si |
| Ingesta a Bronze (streaming) | no Auto Loader | si |
| Promoción a Silver, las tres estrategias | si | si |
| Change Data Feed | si | si |
| Construcción de Gold | si | si |
| Unity Catalog, tablas externas, volúmenes | no | si |

Auto Loader (`cloudFiles`) es propietario de Databricks y no tiene sustituto.
El Change Data Feed, en cambio, es Delta OSS y funciona igual en ambos sitios.

## Los tests

```bash
cd use_cases/cdc
~/.venvs/tfm-cdc/bin/pytest
```

Cubren la lógica de negocio: los generadores, las transformaciones que calculan
los indicadores y la conformidad del resultado con el contrato de Gold. No
tocan Delta ni el catálogo, así que tardan segundos.

Es la parte que ninguna librería resuelve por ti. La ingesta viene resuelta;
el cálculo es propio, y es donde aparecieron los tres errores que producían
datos incorrectos sin que nada fallara.

| Caso | Tests | Qué cubren |
|---|---|---|
| batch | 13 | Generador de ventas y KPIs diarios |
| streaming | 7 | Cliente de la API y agregación por ventana |
| cdc | 7 | Simulador de eventos, cartera e histórico |
| cdf | 9 | Qué estados recalcular y cuáles vaciar |

## Lo que la ejecución local no sustituye

Los fallos más caros de este proyecto **no se habrían detectado en local**:
`EXECUTION_ENVIRONMENT` resolviéndose por `workspace_id`, los volúmenes de
Unity Catalog sin soporte de append, `first_on_demand` en single-node, la
pérdida de logs en `abfss://`. Todos son de entorno.

La ejecución local cubre la lógica de datos. El entorno hay que probarlo en el
entorno.
