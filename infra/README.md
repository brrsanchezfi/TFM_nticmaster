# Infraestructura (Terraform)

## Contexto: el TFM no parte de una suscripción vacía

El TFM se despliega sobre un **workspace corporativo compartido**, no sobre
infraestructura propia creada desde cero. Esto condiciona todo lo que hay en
esta carpeta: casi todos los recursos ya existen y pertenecen a la empresa, y
la cuenta que ejecuta Terraform es **Contributor únicamente del Resource
Group** `rg-demo-eastus2`.

Por tanto, Terraform aquí **no crea plataforma: la consume**. Solo crea lo que
es exclusivamente del TFM y se puede borrar al terminar sin afectar a nadie.

### Recursos preexistentes (se leen con `data`, nunca se modifican)

| Recurso | Nombre | Detalle |
|---|---|---|
| Suscripción | `Microsoft Subscription` | `e348dcd6-db13-458b-a54e-df73a0925a1d` |
| Resource Group | `rg-demo-eastus2` | eastus2 |
| Databricks Workspace | `lakehousedkops` | SKU premium, `adb-7405612310572963.3` |
| ADLS Gen2 | `lakehousedkops` | HNS activo; contenedores `landing`, `bronze`, `silver`, `gold`, `lakehouse` |
| Access Connector | `acc-DKOps` | respalda la storage credential `sc_dkops` |
| Metastore Unity Catalog | `metastore-eastus2` | compartido, propiedad del equipo de plataforma |
| SQL Warehouse | `Serverless Starter Warehouse` | Small, auto-stop 10 min |

### Recursos que sí crea el TFM

| Recurso | Cantidad | Notas |
|---|---|---|
| Catálogos UC | 3 | `bronze_tfm`, `silver_tfm`, `gold_tfm` |
| Schemas UC | 12 | `batch`, `streaming`, `cdc`, `cdf` en cada catálogo |
| Azure SQL serverless | 1 (opcional) | origen del caso CDC; desactivado por defecto |

El sufijo `_tfm` existe para no colisionar con los catálogos de trabajo que ya
viven en el mismo metastore (`bronze_dkops`, `silver_pr`, `gold_ml`…). Los
datos gestionados de cada catálogo cuelgan de la carpeta `tfm/` dentro del
contenedor de su capa, de modo que el TFM queda separado físicamente del resto
sin necesidad de una cuenta de almacenamiento nueva.

Los ficheros de entrada aterrizan en `abfss://landing@lakehousedkops.dfs.core.windows.net/tfm/`,
reutilizando el contenedor y la external location que ya existen.

## Decisiones de alcance

- **Sin red propia.** No se despliega VNet, subredes ni Private Link: se usa
  la red existente del workspace. Por eso no hay módulo `networking`.
- **Sin gestionar lo ajeno.** El workspace y el storage no se importan al
  state: ponerlos bajo un `terraform destroy` accidental sería inaceptable en
  un entorno compartido. Por eso no hay módulos `resource_group`, `storage` ni
  `databricks_workspace`.
- **Sin contraseñas.** El servidor SQL usa autenticación exclusivamente por
  Entra ID (`azuread_authentication_only`), así que no hay ningún secreto que
  guardar ni que acabe en el state.
- **State local.** Lo despliega una sola persona. Si se comparte, mover a un
  backend `azurerm`.

## Limitación conocida: el caso de uso CDC

El módulo `sql_database` está escrito y validado, pero llega **desactivado**
(`enable_cdc_sql = false`). El motivo no es de diseño:

    $ az provider show -n Microsoft.Sql --query registrationState -o tsv
    NotRegistered

Registrar un resource provider es una operación **a nivel de suscripción**, y
la cuenta del TFM es Contributor solo del Resource Group. Con el provider sin
registrar, `terraform apply` fallaría con `MissingSubscriptionRegistration`.

Para habilitarlo, alguien con permisos de suscripción debe ejecutar:

    az provider register --namespace Microsoft.Sql

y después basta con poner `enable_cdc_sql = true` y rellenar
`sql_entra_admin_object_id`. Si no se consigue ese permiso, la alternativa sin
infraestructura es simular los cambios CDC generando ficheros con `op_type`
(I/U/D) directamente en la landing zone: el patrón `cdc_merge` de DKOps queda
demostrado igual.

## Uso

    cd infra/envs/dev
    cp terraform.tfvars.example terraform.tfvars   # ajustar si hace falta

    az login                                        # autenticación de ambos providers
    terraform init
    terraform plan                                  # 15 to add, 0 to change, 0 to destroy
    terraform apply

El provider de Databricks se autentica contra el workspace reutilizando la
sesión de `az`, así que no hace falta ni token personal ni `databricks
configure`.

## Estructura

    infra/
    ├── envs/dev/              # composición del entorno dev
    └── modules/
        ├── unity_catalog/     # catálogos, schemas y grants del TFM
        └── sql_database/      # Azure SQL serverless para CDC (opcional)
