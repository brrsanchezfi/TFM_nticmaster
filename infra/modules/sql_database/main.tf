terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# Origen del caso de uso CDC: una base SQL pequeña donde un generador simula
# INSERT/UPDATE/DELETE sobre la tabla de clientes.
#
# Requisito previo: el provider Microsoft.Sql debe estar registrado en la
# suscripcion. Ver la variable enable_cdc_sql en envs/dev.
resource "azurerm_mssql_server" "this" {
  name                = var.server_name
  resource_group_name = var.resource_group_name
  location            = var.location
  version             = "12.0"

  # Sin usuario/contraseña SQL: solo Entra ID. Evita gestionar secretos y
  # evita que una credencial acabe en el state de Terraform.
  azuread_administrator {
    login_username              = var.entra_admin_login
    object_id                   = var.entra_admin_object_id
    azuread_authentication_only = true
  }

  minimum_tls_version           = "1.2"
  public_network_access_enabled = true

  tags = var.tags
}

# Serverless con auto-pause: fuera de las sesiones de trabajo el coste de
# computo cae a cero y solo se paga el almacenamiento.
resource "azurerm_mssql_database" "this" {
  name      = var.database_name
  server_id = azurerm_mssql_server.this.id

  sku_name                    = "GP_S_Gen5_2"
  min_capacity                = var.min_capacity
  auto_pause_delay_in_minutes = var.auto_pause_delay_in_minutes
  max_size_gb                 = var.max_size_gb

  collation = "SQL_Latin1_General_CP1_CI_AS"

  # PoC: no se necesita retencion geografica ni backups de larga duracion.
  storage_account_type = "Local"

  tags = var.tags
}

# El TFM no despliega red propia: el acceso es por endpoint publico acotado
# con firewall a las IPs indicadas.
resource "azurerm_mssql_firewall_rule" "allowed" {
  for_each = var.allowed_ips

  name             = each.key
  server_id        = azurerm_mssql_server.this.id
  start_ip_address = each.value
  end_ip_address   = each.value
}

# Regla especial 0.0.0.0: habilita el acceso desde servicios de Azure, que es
# como llega el job de Databricks (IP de salida no fija).
resource "azurerm_mssql_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
