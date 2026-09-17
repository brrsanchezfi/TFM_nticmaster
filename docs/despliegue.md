# Despliegue

Cada caso de uso se despliega con su propio Databricks Asset Bundle.

## Contenido de un bundle

`databricks.yml` y `resources/` declaran:

- el job, con sus tareas y dependencias
- el job cluster: runtime 16.4 LTS (Spark 3.5.2), un solo nodo y la etiqueta
  `proyecto=TFM-NTIC-Master`
- el wheel con el código del caso, que se construye al desplegar
- el dashboard AI/BI
- los contratos y la configuración que lee el job

Los catálogos y esquemas no forman parte de ningún bundle. Se crearon una vez y
son comunes a los cuatro casos.

## Validar y desplegar

    cd use_cases/batch
    databricks bundle validate -t dev
    databricks bundle deploy -t dev

`validate` comprueba la configuración sin tocar el workspace. `deploy` construye
el wheel, sube los ficheros y crea o actualiza el job y el dashboard.

Para desplegar los cuatro casos:

    scripts/deploy_all.sh

## Lanzar un job

Los jobs se lanzan por API:

    databricks api post /api/2.2/jobs/run-now --json '{"job_id": <id>}'

`bundle run` espera a que termine el job. Con jobs largos el token de Entra ID
caduca antes (dura una hora) y el cliente falla con
`Token is expiring within 30 seconds`, aunque el job siga ejecutándose sin
problemas. Lanzarlo por API y consultar el estado después evita ese error.

Los casos CDC y CDF aceptan el parámetro `lote`. Con `0`, el valor por defecto,
cada ejecución genera cambios distintos. Con un valor explícito el lote es
reproducible:

    databricks api post /api/2.2/jobs/run-now \
      --json '{"job_id": <id>, "job_parameters": {"lote": "7"}}'

## Detalles de configuración

- **El wheel se construye en local.** El despliegue ejecuta `python -m build`,
  así que el entorno desde el que se lanza necesita el paquete `build`. Desde la
  extensión de VS Code conectada a un cluster falla con
  `No module named build`, porque usa el Python del cluster.
- **La raíz del bundle se pasa como parámetro.** El wheel se instala en
  `site-packages` y el código no puede localizar los contratos desde
  `__file__`:

  ```yaml
  named_parameters:
    bundle-root: ${workspace.file_path}
    config: config/config.dev.json
  ```

- **Un entry point por tarea.** Cada `python_wheel_task` llama a una función
  declarada en `[project.scripts]` del `pyproject.toml`.
- **`first_on_demand: 1`.** En un cluster de un solo nodo la única máquina es el
  driver, y Azure exige que sea bajo demanda.

## Sin Terraform ni CI/CD

No hay Terraform porque el workspace, el almacenamiento y el metastore son
compartidos y el trabajo solo necesitaba crear catálogos y esquemas una vez. Un
fichero de estado sobre ese entorno sería un riesgo.

No hay CI/CD porque un pipeline necesita una identidad propia, un service
principal, y crearlo requiere una App Registration en Entra ID que la cuenta no
puede hacer. `bundle validate` y `bundle deploy` se pueden automatizar sin
cambios en el repositorio cuando exista esa identidad.
