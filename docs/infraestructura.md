# Infraestructura

## Entorno

El trabajo se despliega sobre un workspace corporativo de pruebas que ya
existía y que comparten otros equipos. El workspace, la cuenta de
almacenamiento, el access connector, el metastore y el SQL Warehouse son
preexistentes. Los permisos disponibles son:

- Contributor sobre el grupo de recursos, no sobre la suscripción.
- En el metastore: `CREATE_CATALOG`, `CREATE_EXTERNAL_LOCATION` y
  `CREATE_STORAGE_CREDENTIAL`.

## Qué crea el trabajo

| Recurso | Detalle |
|---|---|
| Catálogos | `bronze_tfm`, `silver_tfm`, `gold_tfm` |
| Esquemas | `batch`, `streaming`, `cdc` y `cdf` en cada catálogo, y `gold_tfm.ops` |
| Tablas | 23 de los casos y la tabla de control, todas externas |
| Volúmenes | Sobre la landing, para subir y leer ficheros |
| Jobs y dashboards | Uno de cada por caso, desplegados con su bundle |

Los catálogos y esquemas se crearon una vez por API. El resto lo despliegan los
bundles.

## Aislamiento

- **Sufijo `_tfm` en los catálogos.** El metastore ya tiene catálogos de otros
  equipos, y los nombres `bronze`, `silver` y `gold` estaban ocupados. El
  sufijo también permite localizar y retirar todo lo del trabajo.
- **Carpeta `tfm/` en cada contenedor.** Los contenedores de cada capa ya
  existían y tienen datos de otros proyectos. Cada catálogo fija su
  `storage_root` en la carpeta `tfm/` del contenedor de su capa.
- **Sin infraestructura como código.** Un fichero de estado de Terraform sobre
  recursos compartidos permitiría borrarlos con un `destroy`. Como el trabajo
  solo necesita crear catálogos y esquemas una vez, se hizo por API.

## Autenticación

La CLI de Databricks usa un token de Entra ID obtenido con la sesión de Azure
CLI. No hay tokens personales ni credenciales en ficheros.

El acceso al lago se hace con la identidad gestionada del access connector, a
través de Unity Catalog. El usuario no tiene rol de datos sobre la cuenta de
almacenamiento, así que la subida de ficheros a la landing se hace con la CLI de
Databricks sobre un volumen:

    databricks fs cp ventas.json dbfs:/Volumes/bronze_tfm/batch/landing/ventas/

## Red

El trabajo usa la red del workspace, configurado sin IP pública. No hay VNet
injection ni Private Link.

## Origen del caso CDC

El diseño preveía Azure SQL con Change Tracking. El proveedor `Microsoft.Sql` no
está registrado en la suscripción y registrarlo requiere permisos que no hay. El
caso usa un simulador que escribe en la landing eventos con `op_type` (`I`, `U`,
`D`) y `op_ts`, el mismo formato que produciría Change Tracking.

## Tablas externas

Cada contrato declara `type: EXTERNAL` y una ubicación que reproduce el nombre
lógico de la tabla:

    abfss://<capa>@<cuenta>.dfs.core.windows.net/<catalogo>/<esquema>/<tabla>

Por ejemplo, `silver_tfm.batch.ventas` está en
`abfss://silver@<cuenta>.dfs.core.windows.net/silver_tfm/batch/ventas`. Con
tablas gestionadas, Unity Catalog las guardaría en
`__unitystorage/catalogs/<uuid>/`.

La tabla de control es la excepción: vive en la landing, en `tfm/_ops/ingestas`,
y se registra aparte (ver [observabilidad.md](observabilidad.md)).

## Restricciones de Unity Catalog

**`DROP TABLE` no borra los ficheros de una tabla externa.** Al recrearla, el
`CREATE` encuentra los datos anteriores y falla:

    DELTA_CREATE_TABLE_SCHEME_MISMATCH

**Un volumen y una tabla externa no pueden compartir ruta**, en ningún sentido.
Crear una tabla dentro de un volumen falla con `PATH_CREATE_TABLE on volume`, y
Unity Catalog tampoco deja crear un volumen sobre una ruta con tablas.

Por eso, para reconstruir el entorno desde cero:

1. `DROP` de las tablas.
2. Crear un volumen sobre la raíz de la capa.
3. Borrar los ficheros.
4. Eliminar el volumen.
5. Ejecutar los pipelines, que recrean las tablas.

Los volúmenes que se mantienen están en carpetas de la landing donde no hay
ninguna tabla. La carpeta `tfm/_ops` de la tabla de control queda fuera de
ellos.
