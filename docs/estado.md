# Estado del proyecto

Última actualización: 18 de agosto de 2026.

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
| 7 | Caso de uso **CDC** | ⬜ bloqueado parcialmente |
| 8 | Caso de uso **Streaming** | ⬜ |
| 9 | CI/CD (GitHub Actions) | ⬜ workflows vacíos |
| 10 | Documentación final | 🔶 parcial |
| 11 | Revisión y defensa | ⬜ |

## Qué funciona hoy

**Batch** (`retail_sales`) — Landing → Bronze → Silver → Gold, ejecutado en
Databricks con dashboard de consumo.

| Capa | Filas |
|---|---|
| Landing / Bronze | 525 |
| Silver | 500 (25 duplicadas colapsadas por `full_merge`) |
| Gold | 249 agregados |

**CDF** (`orders`) — propagación incremental verificada con tres ejecuciones
encadenadas: puntero v24 → v27 → v31, sin solapamientos, 360 filas y 360
`pedido_id` únicos. Dashboard con el puntero y la marca de recálculo.

**Unity Catalog** — `bronze_tfm`, `silver_tfm` y `gold_tfm`, con un schema por
caso de uso, sobre la carpeta `tfm/` de los contenedores de `lakehousedkops`.

## Criterios de éxito del TFM

- [x] Cada caso ejecuta su pipeline completo sin intervención manual — **2 de 4**
- [ ] Los 4 bundles se validan y despliegan de forma independiente — 2 de 4 desplegados, los 4 validan
- [ ] CDC captura INSERT/UPDATE/DELETE simulados
- [ ] Streaming ingiere desde la API pública
- [x] CDF demuestra procesamiento incremental
- [x] Unity Catalog organiza catálogos, schemas y tablas por capa y caso
- [ ] Documentación completa y navegable sin leer código
- [x] Diagramas versionados en Mermaid

## Bloqueos abiertos

**`Microsoft.Sql` sin registrar.** El caso CDC no puede crear su Azure SQL:
registrar un resource provider es una operación de suscripción y la cuenta es
Contributor solo del Resource Group. Hace falta que alguien con permisos
ejecute `az provider register --namespace Microsoft.Sql`. Alternativa sin
bloqueo: simular los cambios con ficheros que lleven `op_type`.

**Sin App Registrations en Entra ID.** La política del tenant lo impide, lo que
afecta al CI/CD con OIDC. Rodeo previsto: usar un service principal de
Databricks en lugar de uno de Entra.

**State de Terraform vacío.** Los catálogos se crearon por API, así que un
`terraform apply` fallaría con "already exists". Queda decidir entre importar
los recursos o documentar Terraform como demostración de IaC.

## Deuda técnica

- El caso Streaming aún tiene la estructura genérica del scaffold; habrá que
  adaptarla como se hizo con CDF.
- Los 5 workflows de GitHub Actions son ficheros de 10 líneas sin contenido.
- 11 de 14 páginas de `docs/` siguen pendientes de redactar.

## Incidencias reportadas en DKOps

- `add_silver_timestamps` promete `_silver_created_at` y `_silver_modified_at`,
  pero la promoción a Silver solo genera la segunda.
- El tag `v0.3.0` construye un wheel que se identifica como `0.2.4`.
