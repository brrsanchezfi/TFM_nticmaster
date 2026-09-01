# Infraestructura

## El punto de partida real

El diseño inicial del TFM asumía una suscripción de Azure vacía sobre la que
Terraform crearía la plataforma completa: Resource Group, cuenta de
almacenamiento, workspace de Databricks y catálogos de Unity Catalog. El
inventario del entorno demostró que la realidad era otra, y merece la pena
documentarlo porque es un escenario mucho más habitual en la práctica
profesional que el de la suscripción en blanco: **la plataforma ya existe y es
compartida**.

El TFM se despliega sobre el workspace corporativo `lakehousedkops`, dentro de
un Resource Group donde ya conviven recursos de otros proyectos, y contra un
metastore de Unity Catalog que aloja los catálogos de trabajo de varios
compañeros. Los permisos disponibles son:

- **Contributor** con alcance del Resource Group `rg-demo-eastus2`
  (no de la suscripción).
- Sobre el metastore: `CREATE_CATALOG`, `CREATE_EXTERNAL_LOCATION` y
  `CREATE_STORAGE_CREDENTIAL`.

Esto cambia el papel de la infraestructura como capa: el ejercicio deja de ser
"crear una plataforma" y pasa a ser "insertarse en una plataforma ajena sin
romperla", que impone restricciones más interesantes.

## Qué existe y qué crea el TFM

| Capa | Recurso | ¿Quién lo gestiona? |
|---|---|---|
| Cómputo | Workspace `lakehousedkops` (premium, eastus2) | Preexistente — solo lectura |
| Almacenamiento | ADLS Gen2 `lakehousedkops`, HNS activo | Preexistente — solo lectura |
| Identidad de storage | Access Connector `acc-DKOps` → credencial `sc_dkops` | Preexistente — solo lectura |
| Gobierno | Metastore `metastore-eastus2` | Preexistente — solo lectura |
| Consumo | `Serverless Starter Warehouse` | Preexistente — reutilizado |
| Gobierno | Catálogos `bronze_tfm`, `silver_tfm`, `gold_tfm` | **Terraform** |
| Gobierno | 12 schemas (`batch`, `streaming`, `cdc`, `cdf` × 3 capas) | **Terraform** |
| Origen CDC | Azure SQL serverless | **Terraform**, desactivado (ver más abajo) |

La prueba de que el aislamiento funciona es el propio plan de Terraform:

    Plan: 15 to add, 0 to change, 0 to destroy.

Ni una sola modificación sobre recursos existentes.

## Estrategia de aislamiento

Tres decisiones sostienen la convivencia con el entorno compartido:

1. **Sufijo `_tfm` en los catálogos.** El metastore ya contiene
   `bronze_dkops`, `silver_pr`, `gold_ml`, `bronze_demo`… Crear catálogos
   llamados `bronze`/`silver`/`gold` habría sido una colisión de nombres en un
   espacio compartido. El sufijo también hace trivial identificar y borrar todo
   lo del TFM al terminar.

2. **Carpeta `tfm/` dentro de cada contenedor.** Los contenedores `bronze`,
   `silver`, `gold` y `landing` ya existen y contienen datos de trabajo
   (`aeronautica`, `manufactura`). En lugar de crear una cuenta de
   almacenamiento nueva —coste y complejidad añadidos— cada catálogo del TFM
   fija su `storage_root` en la subcarpeta `tfm/` del contenedor de su capa. La
   separación es física, pero sin recursos nuevos.

3. **Nada ajeno entra en el state.** El workspace y el storage se referencian
   con `data` sources, nunca con `import`. Un recurso en el state es un recurso
   que un `terraform destroy` puede borrar; en un entorno compartido eso no es
   un riesgo aceptable ni siquiera como demostración.

## Red

El TFM no despliega red propia: reutiliza la del workspace, que ya está
configurado con *no public IP*. No hay VNet injection ni Private Link. Es una
decisión de alcance consciente —el objeto de estudio son los patrones de
ingesta, no la topología de red— y queda recogida como trabajo futuro.

## Autenticación

Ambos providers se autentican con la sesión de Azure CLI: `azurerm` de forma
directa, y `databricks` mediante `azure_workspace_resource_id`, que obtiene un
token AAD para el workspace. No hace falta ningún *personal access token* ni
credenciales en ficheros.

Para el servidor SQL se usa autenticación **exclusivamente por Entra ID**
(`azuread_authentication_only = true`), de modo que no existe ninguna
contraseña que rotar, ni que compartir, ni que pueda filtrarse a través del
fichero de estado de Terraform.

## Limitación abierta: el origen del caso CDC

El módulo `sql_database` está escrito y validado, pero se entrega desactivado
mediante la variable `enable_cdc_sql`. El motivo es un límite de permisos, no
de diseño: el resource provider `Microsoft.Sql` figura como `NotRegistered` en
la suscripción, y registrarlo es una operación de ámbito de suscripción que
Contributor sobre un Resource Group no autoriza. Un `apply` con el módulo
activo fallaría con `MissingSubscriptionRegistration`.

Hay dos salidas, y ambas dejan el caso de uso CDC igual de bien demostrado:

- **Con Azure SQL**: alguien con permisos de suscripción ejecuta
  `az provider register --namespace Microsoft.Sql`, y basta con poner
  `enable_cdc_sql = true`.
- **Sin Azure SQL**: el generador de datos escribe directamente en la landing
  zone ficheros con la columna `op_type` (I/U/D). Lo que el TFM demuestra es el
  patrón `cdc_merge` sobre la capa Silver —incluido el *soft delete*—, y ese
  patrón es idéntico venga el cambio de Change Tracking o de un fichero.

## Tablas externas y convención de rutas

Las 13 tablas del TFM se declaran `EXTERNAL` en su contrato, con una ubicación
que reproduce su nombre lógico:

    abfss://<capa>@lakehousedkops.dfs.core.windows.net/<catálogo>/<esquema>/<tabla>

Por ejemplo, `silver_tfm.batch.ventas` vive en
`abfss://silver@…/silver_tfm/batch/ventas`. Frente a dejarlas gestionadas
—donde Unity Catalog las coloca en `__unitystorage/catalogs/<uuid>/…`— esto
aporta dos cosas: el almacenamiento es legible sin consultar el catálogo, y el
ciclo de vida del dato queda bajo control del proyecto.

Esa segunda parte tiene una contrapartida que conviene tener presente:

**`DROP TABLE` sobre una tabla externa no borra los ficheros.** Elimina el
registro del catálogo y deja los datos Delta en su ruta. Al recrear la tabla,
el `CREATE OR REPLACE` choca con lo que quedó:

    DELTA_CREATE_TABLE_SCHEME_MISMATCH
    The specified schema does not match the existing schema at abfss://…

Con tablas gestionadas el borrado se lleva los datos; con externas, vaciar el
almacenamiento es responsabilidad de quien opera.

### Volúmenes y tablas no pueden compartir ruta

Para borrar ficheros hace falta acceso POSIX, y eso significa un volumen de
Unity Catalog. Pero un volumen y una tabla externa **no pueden convivir en la
misma ruta**: crear una tabla dentro del territorio de un volumen falla con

    Unsupported path operation PATH_CREATE_TABLE on volume

Y al revés: UC rechaza crear un volumen sobre una ruta que ya contiene tablas
externas registradas. El orden para reconstruir el entorno desde cero es, por
tanto:

1. `DROP` de las tablas — antes, el volumen se rechaza por solapamiento.
2. Crear el volumen sobre la raíz de la capa.
3. Borrar los ficheros.
4. **Eliminar el volumen** — si se queda, bloquea la creación de las tablas.
5. Ejecutar los pipelines, que recrean las tablas en su ruta.

Los volúmenes que sí permanecen en el proyecto cubren únicamente el contenedor
`landing`, donde no vive ninguna tabla: la zona de aterrizaje de batch y CDC, y
la carpeta de logs.

## Coste

Los únicos recursos que el TFM añade son objetos de Unity Catalog, que **no
tienen coste**. El gasto real se reduce a los minutos de job cluster que
consuman las ejecuciones, al almacenamiento de unos pocos GB, y —si se llega a
habilitar— a una base SQL serverless que se autopausa a los 60 minutos.
