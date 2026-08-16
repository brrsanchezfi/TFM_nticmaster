########################################
# Recursos preexistentes (solo lectura)
#
# El TFM se despliega sobre un workspace corporativo compartido. Nada de lo
# que hay aqui se crea ni se modifica: se referencia con data sources para
# que Terraform pueda componer identificadores sin tocar los recursos.
########################################

data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

data "azurerm_databricks_workspace" "this" {
  name                = var.databricks_workspace_name
  resource_group_name = data.azurerm_resource_group.this.name
}

data "azurerm_storage_account" "lakehouse" {
  name                = var.storage_account_name
  resource_group_name = data.azurerm_resource_group.this.name
}

# Metastore ya asignado al workspace (propiedad del equipo de plataforma).
data "databricks_current_metastore" "this" {}

########################################
# Unity Catalog del TFM
########################################

module "unity_catalog" {
  source = "../../modules/unity_catalog"

  catalog_suffix = var.catalog_suffix
  use_cases      = var.use_cases
  owner          = var.catalog_owner
  extra_readers  = var.extra_readers

  storage_account_name   = data.azurerm_storage_account.lakehouse.name
  managed_storage_prefix = var.managed_storage_prefix
}

########################################
# Azure SQL para el caso de uso CDC (opcional)
########################################

module "sql_database" {
  source = "../../modules/sql_database"
  count  = var.enable_cdc_sql ? 1 : 0

  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location

  server_name   = var.sql_server_name
  database_name = var.sql_database_name

  entra_admin_login     = var.sql_entra_admin_login
  entra_admin_object_id = var.sql_entra_admin_object_id
  allowed_ips           = var.sql_allowed_ips

  tags = var.tags
}
