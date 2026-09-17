# Ejecución local

Los pipelines se pueden ejecutar sin Databricks, salvo la ingesta de streaming,
que usa Auto Loader.

## Entornos

Cada caso tiene su `pyproject.toml` y su entorno virtual:

```bash
for uc in batch streaming cdc cdf; do
  python3 -m venv ~/.venvs/tfm-$uc
  ~/.venvs/tfm-$uc/bin/pip install -e "use_cases/$uc[local]"
done
```

El extra `[local]` instala `pyspark 3.5.3`, `delta-spark 3.2.0` y `pytest`. En
Databricks no se instala, porque Spark y Delta los aporta el runtime.

En WSL, los entornos van en el sistema de ficheros de Linux y no bajo `/mnt/c`:
sobre el montaje de Windows la instalación tarda decenas de minutos.

## Configuración

Cada caso tiene un `config/config.local.json` además del de Databricks:

| Campo | Valor en local |
|---|---|
| `EXECUTION_ENVIRONMENT` | `local`: crea una SparkSession normal |
| `DATABRICKS_TARGET` | `local`: el entorno se resuelve por nombre |
| `SPARK_WAREHOUSE_DIR` | Carpeta donde Spark guarda las tablas |

Las rutas apuntan a `/tmp/<caso>/` y los catálogos no llevan el sufijo `_tfm`.
Sin Unity Catalog, las tablas se registran con nombre de dos partes, por ejemplo
`batch.ventas`.

## Qué se puede ejecutar

| Pieza | Local | Databricks |
|---|---|---|
| Generadores y simuladores | sí | sí |
| Ingesta a bronze en batch y CDC | sí | sí |
| Ingesta a bronze en streaming (Auto Loader) | no | sí |
| Promoción a silver | sí | sí |
| Change Data Feed | sí | sí |
| Construcción de gold | sí | sí |
| Unity Catalog, tablas externas y volúmenes | no | sí |

## Pruebas

```bash
cd use_cases/cdc
~/.venvs/tfm-cdc/bin/pytest
```

Prueban los generadores y la lógica de negocio. No usan Delta ni el catálogo y
tardan segundos.

| Caso | Pruebas | Qué cubren |
|---|---|---|
| batch | 13 | Generador de ventas y KPIs diarios |
| streaming | 7 | Cliente de la API y agregación por ventana |
| cdc | 7 | Simulador de eventos, cartera e histórico |
| cdf | 9 | Estados a recalcular y estados que se vacían |

La ejecución local no sustituye a Databricks. Los fallos de entorno recogidos en
[estado.md](estado.md) solo aparecieron al ejecutar en el workspace.
