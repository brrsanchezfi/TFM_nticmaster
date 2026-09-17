# Documentación técnica

Documentación de la plataforma lakehouse del TFM. La descripción general está
en el [README](../README.md) del repositorio, y cada caso de uso se documenta
junto a su código.

## Casos de uso

| Caso | Documentación |
|---|---|
| Batch | [use_cases/batch](../use_cases/batch/README.md) |
| Streaming | [use_cases/streaming](../use_cases/streaming/README.md) |
| CDC | [use_cases/cdc](../use_cases/cdc/README.md) |
| CDF | [use_cases/cdf](../use_cases/cdf/README.md) |

## Páginas

| Página | Contenido |
|---|---|
| [Estado](estado.md) | Fases, cifras de la última ejecución e incidencias |
| [Infraestructura](infraestructura.md) | Entorno compartido, Unity Catalog y tablas externas |
| [Observabilidad](observabilidad.md) | Tabla de control de ejecuciones y logs |
| [Ejecución local](ejecucion-local.md) | Entornos, configuración local y pruebas |
| [Despliegue](despliegue.md) | Asset Bundles y lanzamiento de jobs |
| [Costes](costes.md) | Consumo medido y consultas para obtenerlo |

La documentación se puede servir con MkDocs desde la raíz del repositorio:

    pip install mkdocs-material
    mkdocs serve
