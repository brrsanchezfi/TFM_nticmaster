# Changelog

## [Unreleased]
- Scaffolding inicial del repositorio.
- Fase 2 — Infraestructura como código (Terraform):
  - Inventario del entorno real: el TFM se despliega sobre el workspace
    corporativo compartido `lakehousedkops`, no sobre una suscripción vacía.
  - Módulo `unity_catalog`: catálogos `bronze_tfm`/`silver_tfm`/`gold_tfm` y un
    schema por caso de uso, aislados de los catálogos del equipo.
  - Módulo `sql_database`: Azure SQL serverless para el caso CDC, con
    autenticación solo Entra ID. Desactivado por defecto: el provider
    `Microsoft.Sql` está sin registrar en la suscripción.
  - Los recursos preexistentes (RG, storage, workspace, metastore) se leen con
    `data` sources; el plan confirma `0 to change, 0 to destroy`.
  - Se descartan los módulos `resource_group`, `storage`,
    `databricks_workspace` y `networking`: nada de eso lo crea el TFM.
  - Las configuraciones `dev` de los 4 casos de uso apuntan a los catálogos
    `*_tfm`.
