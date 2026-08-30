# Estado del proyecto

Última actualización: 24 de agosto de 2026.

## Roadmap

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Diseño | ✅ |
| 1 | Scaffolding del repositorio | ✅ |
| 2 | Terraform (Unity Catalog) | ✅ escrito y validado, **no aplicado** |
| 3 | Catálogos y schemas en el workspace | ✅ desplegado por API |
| 4 | DKOps como dependencia + 4 bundles | ✅ |
| 5 | Caso de uso **Batch** | ✅ ejecutado end-to-end |
| 6 | Caso de uso **CDF** | ✅ ejecutado end-to-end |
| 7 | Caso de uso **CDC** | ✅ ejecutado end-to-end |
| 8 | Caso de uso **Streaming** | ✅ ejecutado end-to-end |
| 9 | CI/CD (GitHub Actions) | ⬜ workflows vacíos |
| 10 | Documentación final | 🔶 5 de 14 páginas |
| 11 | Revisión y defensa | ⬜ |

## Lo que funciona hoy

**Los cuatro casos de uso** están desplegados y ejecutados en Databricks, cada
uno con su dashboard de consumo: 4 jobs, 4 dashboards y 13 tablas repartidas en
los tres catálogos.

| Caso | Estrategia | Evidencia de la ejecución |
|---|---|---|
| Batch | `full_merge` | 525 filas en Bronze → 500 en Silver (25 reemisiones colapsadas) → 249 agregados |
| Streaming | `append_dedup` | Auto Loader con `availableNow`; 10 observaciones → 5 ventanas horarias |
| CDF | — | Puntero de versiones v24 → v27 → v31, sin solapamientos |
| CDC | `cdc_merge` | 200/240/280 eventos en Bronze frente a 200/210/220 clientes en Silver |

El contraste entre las tres estrategias de promoción es uno de los resultados
más ilustrativos del trabajo: **las tres son una línea distinta en un fichero
JSON**, y el código de los cuatro casos es el mismo.

## Criterios de éxito

Del núcleo evaluable, **7 de 8**:

- [x] Cada caso ejecuta su pipeline completo sin intervención manual
- [x] Los 4 Asset Bundles se validan y despliegan de forma independiente
- [x] CDC captura y procesa INSERT/UPDATE/DELETE
- [x] Streaming ingiere desde una API pública
- [x] CDF demuestra procesamiento incremental
- [x] Unity Catalog organiza catálogos, schemas y tablas por capa y caso
- [ ] Documentación completa y navegable sin leer código
- [x] Diagramas versionados en Mermaid

## Incidencias reportadas a DKOps

Cinco detectadas durante la implementación, **las cinco corregidas**:

| # | Incidencia | Corregida en |
|---|---|---|
| 1 | `add_silver_timestamps` no generaba `_silver_created_at` | v0.3.1 |
| 2 | El tag `v0.3.0` producía un wheel identificado como `0.2.4` | v0.3.1 |
| 3 | Los comentarios del contrato solo llegaban a Unity Catalog vía `CreateWriter` | v0.3.1 |
| 4 | `cdc_merge` dejaba `is_deleted` a NULL si la columna venía en el DataFrame | pendiente |
| 5 | `license = "MIT"` (PEP 639) exigía `setuptools>=77` con `build-system` en `>=68` | v0.3.2 |

La quinta es la más instructiva: se introdujo **al corregir las tres primeras**
y solo se manifestaba en el cluster, no en un entorno de desarrollo. Ninguna
tarea llegaba a arrancar.

## Fallos que solo aparecieron al ejecutar

Merecen su sitio en la memoria, porque ninguno lo habrían detectado los tests:

- **`EXECUTION_ENVIRONMENT` debe ser `local`** dentro de un job cluster, y el
  entorno se resuelve por `workspace_id`, no por nombre.
- **`first_on_demand` debe ser ≥ 1**: en single-node la única VM es el driver
  y Azure exige que sea on-demand. No hay ahorro por spot.
- **`checkpoint` y `schemas` de Auto Loader no pueden vivir en `/tmp`**: con
  clusters efímeros se pierden y cada ejecución reingiere la landing entera.
- **Leer el Change Data Feed desde la versión 0** atraviesa la creación de la
  tabla y Delta lo rechaza. El arranque en frío no debe usar el feed.
- **Una fuga de columnas internas** desde Silver hasta la landing hizo que
  `is_deleted` quedara a NULL, y como `NOT NULL` no es `TRUE`, cinco
  ejecuciones terminaron en verde produciendo datos incorrectos.

## Bloqueos abiertos

**`Microsoft.Sql` sin registrar.** Registrar un resource provider es una
operación de suscripción y la cuenta es Contributor solo del Resource Group.
El caso CDC se resolvió con un origen simulado que emite el mismo contrato de
datos —una fila por evento con `op_type` y `op_ts`—, de modo que el pipeline es
idéntico al que procesaría Change Tracking. El módulo Terraform del Azure SQL
está escrito y validado, listo para `enable_cdc_sql = true`.

**Sin App Registrations en Entra ID.** Afecta al CI/CD con OIDC. Rodeo
previsto: usar un service principal de Databricks.

**State de Terraform vacío.** Los catálogos se crearon por API, así que un
`terraform apply` fallaría con "already exists". Queda decidir entre importar
los recursos o documentar Terraform como demostración de IaC.

## Deuda técnica

- Los 5 workflows de GitHub Actions siguen siendo ficheros de 10 líneas.
- 9 páginas de `docs/` pendientes de redactar: arquitectura (3), stack, costes,
  CI/CD y conclusiones.
- Las rutas con formato `lote=...` hacen que Spark infiera una columna de
  partición no declarada en el contrato (`lote` en la Bronze de streaming).
- Gold se reconstruye completa en los cuatro casos. Con volúmenes reales
  habría que pasar a upserts incrementales.
