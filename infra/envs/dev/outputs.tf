output "workspace_url" {
  description = "URL del workspace de Databricks (preexistente)."
  value       = "https://${data.azurerm_databricks_workspace.this.workspace_url}"
}

output "metastore" {
  description = "Metastore de Unity Catalog al que esta asignado el workspace."
  value = {
    name = data.databricks_current_metastore.this.metastore_info[0].name
    id   = data.databricks_current_metastore.this.metastore_info[0].metastore_id
  }
}

output "catalogs" {
  description = "Catalogos creados por el TFM, por capa."
  value       = module.unity_catalog.catalogs
}

output "schemas" {
  description = "Schemas creados, en formato catalogo.schema."
  value       = module.unity_catalog.schemas
}

output "landing_path" {
  description = "Ruta de la landing zone del TFM dentro del contenedor existente."
  value       = "abfss://landing@${data.azurerm_storage_account.lakehouse.name}.dfs.core.windows.net/${var.managed_storage_prefix}"
}

output "cdc_sql" {
  description = "Datos de conexion del origen CDC, si esta habilitado."
  value = var.enable_cdc_sql ? {
    fqdn     = module.sql_database[0].server_fqdn
    database = module.sql_database[0].database_name
    jdbc     = module.sql_database[0].jdbc_url
  } : null
}
