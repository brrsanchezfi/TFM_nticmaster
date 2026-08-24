# TFM NTIC Master — PoC de ingeniería de datos sobre Databricks/Azure

Implementación de los cuatro patrones habituales de ingeniería de datos
—batch, streaming, CDC y CDF— sobre una arquitectura Lakehouse en Azure y
Databricks, gobernada con Unity Catalog y desplegada con Databricks Asset
Bundles.

## Por dónde empezar

| Documento | Qué contiene |
|---|---|
| [Estado del proyecto](estado.md) | Qué está hecho, qué falta y qué está bloqueado |
| [Infraestructura](infraestructura.md) | El entorno real y las decisiones de aislamiento |
| [Caso Batch](casos_uso/batch.md) | Pipeline completo, el caso piloto |
| [Caso CDF](casos_uso/cdf.md) | Propagación incremental con Change Data Feed |

## Una nota sobre el punto de partida

El diseño inicial asumía una suscripción de Azure vacía sobre la que
provisionar la plataforma entera. El entorno real resultó ser un **workspace
corporativo compartido**, con catálogos de otros equipos en el mismo metastore
y permisos acotados a un Resource Group.

Lejos de ser un contratiempo, es un escenario más representativo del trabajo
profesional que la suscripción en blanco: el ejercicio deja de ser "crear una
plataforma" y pasa a ser "insertarse en una ajena sin romperla". Buena parte de
las decisiones de este TFM —el sufijo `_tfm`, la carpeta propia en cada
contenedor, que Terraform lea con `data` sources en vez de importar— se
entienden desde ahí.
