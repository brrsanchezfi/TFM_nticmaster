# Despliegue

El despliegue se hace con **Databricks Asset Bundles**, uno por caso de uso. No
hay infraestructura como código ni pipeline de CI externo: la decisión y sus
motivos están al final de esta página.

## Qué despliega un bundle

Cada caso de uso declara en su `databricks.yml` y su `resources/jobs.yml` todo
lo necesario para funcionar:

- el **job** con sus tareas y sus dependencias entre ellas
- el **job cluster** que las ejecuta, con su runtime y su tipo de máquina
- el **wheel** con el código del caso, construido en el momento del despliegue
- el **dashboard** AI/BI de consumo
- los **ficheros del bundle** (contratos y configuración) que el job lee en
  ejecución

Es decir, el bundle cubre todo lo que es propio del caso de uso. Lo que queda
fuera son los catálogos y los esquemas de Unity Catalog, que son compartidos y
se crearon una sola vez.

## El ciclo

    cd use_cases/batch
    databricks bundle validate -t dev
    databricks bundle deploy -t dev

`validate` comprueba la sintaxis y resuelve las variables sin tocar el
workspace. `deploy` construye el wheel, sube todo al workspace y crea o
actualiza el job y el dashboard.

Para lanzar el job, conviene usar la API en vez de `bundle run`:

    databricks api post /api/2.2/jobs/run-now --json '{"job_id": <id>}'

`bundle run` se queda bloqueado esperando a que el job termine. Los tokens de
Entra ID duran una hora, así que un job largo acaba con:

    Error: failed to log job run. Error: Token is expiring within 30 seconds.

El job **sigue ejecutándose en el servidor**, pero el cliente pierde el hilo y
el error aparenta ser del pipeline cuando es solo de la sesión. Lanzarlo por
API y consultar el estado después, renovando el token en cada consulta, evita
esa confusión.

## Detalles que costaron una ejecución fallida

**El wheel se construye en local, no en el cluster.** El despliegue invoca
`python -m build`, así que hay que lanzarlo desde un entorno que tenga ese
paquete instalado. Hacerlo desde la extensión de VS Code conectada a un cluster
falla con `No module named build`, porque usa el Python remoto.

**El código acaba en `site-packages`.** El wheel se instala en el cluster, de
modo que el proceso no puede deducir dónde están los contratos a partir de
`__file__`. La raíz del bundle se pasa explícitamente:

```yaml
named_parameters:
  bundle-root: ${workspace.file_path}
  config: config/config.dev.json
```

**Cada tarea necesita su propio entry point.** Un `python_wheel_task` invoca
una función concreta, así que declarar `main` en todas las tareas hace que
todas ejecuten lo mismo. Los entry points se declaran en el `pyproject.toml`
del caso.

**`first_on_demand` debe ser al menos 1.** En un cluster single-node la única
máquina es el driver, y Azure exige que el driver sea on-demand. Se deja
declarada la política de spot para que aplique si algún día se añaden workers,
pero hoy no hay ahorro por esa vía.

## Por qué no hay Terraform

El trabajo se despliega sobre un **workspace corporativo compartido** que ya
existía. El grupo de recursos, la cuenta de almacenamiento, el workspace y el
metastore son de otros, y la cuenta disponible es Contributor solo del grupo de
recursos.

En esas condiciones, un Terraform que gestionara la plataforma sería un
ejercicio artificial: leería con `data` sources casi todo y crearía únicamente
los catálogos y esquemas, que se hacen una vez y no vuelven a tocarse. Peor
aún, tendría un fichero de estado que un `destroy` accidental podría usar para
borrar recursos compartidos.

Se descartó por eso, y no por desconocimiento del patrón. La contrapartida
honesta es que **la creación de los catálogos y esquemas no queda versionada**:
está documentada en [infraestructura.md](infraestructura.md), pero es un paso
manual.

## Por qué no hay CI/CD

Automatizar el despliegue requiere una identidad propia que no sea la de una
persona: un service principal con permisos sobre el workspace. Crearlo exige
una App Registration en Entra ID, y esa es una operación de directorio que la
cuenta disponible no puede hacer.

Sin esa identidad, un pipeline de CI tendría que usar credenciales personales,
que es justo lo que un pipeline no debe hacer.

Lo que sí queda automatizable y reproducible es el propio bundle: `validate` y
`deploy` son deterministas y se ejecutan igual desde cualquier máquina. Un
futuro pipeline solo tendría que invocarlos con una identidad adecuada, sin
cambiar nada del repositorio.

## Estado actual

| Pieza | Estado |
|---|---|
| Bundles por caso de uso | Los cuatro validan y despliegan |
| Jobs con sus tareas y dependencias | Declarados en el bundle |
| Dashboards | Desplegados con el bundle |
| Catálogos y esquemas | Creados por API, no versionados |
| Ejecución del despliegue | Manual, con la sesión del usuario |
| Pruebas antes del despliegue | Manuales, ver [ejecucion-local.md](ejecucion-local.md) |
