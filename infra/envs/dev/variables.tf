########################################
# Azure: todo preexistente, solo lectura
########################################

variable "subscription_id" {
  description = "Suscripcion que contiene el Resource Group del TFM."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group existente. No se crea ni se modifica."
  type        = string
  default     = "rg-demo-eastus2"
}

variable "databricks_workspace_name" {
  description = "Workspace de Databricks existente. No se crea ni se modifica."
  type        = string
  default     = "lakehousedkops"
}

variable "databricks_host" {
  description = "URL del workspace de Databricks."
  type        = string
  default     = "https://adb-7405612310572963.3.azuredatabricks.net"
}

variable "storage_account_name" {
  description = "Cuenta ADLS Gen2 existente que sirve de lakehouse. No se crea ni se modifica."
  type        = string
  default     = "lakehousedkops"
}

########################################
# Unity Catalog: lo unico que crea el TFM
########################################

variable "catalog_suffix" {
  description = <<-EOT
    Sufijo que aisla los catalogos del TFM de los del resto del equipo.
    Con el valor por defecto se crean bronze_tfm / silver_tfm / gold_tfm.
  EOT
  type        = string
  default     = "tfm"
}

variable "use_cases" {
  description = "Un schema por caso de uso dentro de cada catalogo."
  type        = list(string)
  default     = ["batch", "streaming", "cdc", "cdf"]
}

variable "managed_storage_prefix" {
  description = <<-EOT
    Prefijo (carpeta) dentro de cada contenedor donde viven los datos gestionados
    del TFM. Mantiene el TFM separado de los datos de trabajo que ya existen en
    los contenedores bronze/silver/gold.
  EOT
  type        = string
  default     = "tfm"
}

variable "catalog_owner" {
  description = "Principal propietario de los catalogos del TFM."
  type        = string
  default     = "brayan.sanchez@dataknow.co"
}

variable "extra_readers" {
  description = <<-EOT
    Principales adicionales que reciben lectura sobre los catalogos del TFM
    (por ejemplo, un tribunal o un compañero). Vacio por defecto.
  EOT
  type        = list(string)
  default     = []
}

########################################
# Caso de uso CDC: Azure SQL (opcional)
########################################

variable "enable_cdc_sql" {
  description = <<-EOT
    Crea el Azure SQL Database serverless que alimenta el caso de uso CDC.

    Desactivado por defecto a proposito: el provider Microsoft.Sql esta
    NotRegistered en la suscripcion y registrarlo requiere permisos de
    suscripcion (la cuenta actual es Contributor solo del Resource Group).
    Activar solo despues de:
        az provider register --namespace Microsoft.Sql
    ejecutado por alguien con permisos suficientes.
  EOT
  type        = bool
  default     = false
}

variable "sql_server_name" {
  description = "Nombre del servidor logico de Azure SQL (debe ser unico global)."
  type        = string
  default     = "sql-tfm-cdc-eastus2"
}

variable "sql_database_name" {
  description = "Nombre de la base de datos usada como origen CDC."
  type        = string
  default     = "cdc_source"
}

variable "sql_entra_admin_login" {
  description = <<-EOT
    UPN del administrador Entra ID del servidor SQL. Se usa autenticacion
    exclusivamente por Entra ID: el servidor no tiene usuario/contraseña SQL,
    asi no hay secretos que gestionar ni que guardar en el state.
  EOT
  type        = string
  default     = "brayan.sanchez@dataknow.co"
}

variable "sql_entra_admin_object_id" {
  description = <<-EOT
    Object ID en Entra ID del administrador del servidor SQL.
    Obtenerlo con: az ad signed-in-user show --query id -o tsv
  EOT
  type        = string
  default     = ""
}

variable "sql_allowed_ips" {
  description = <<-EOT
    IPs publicas autorizadas a conectar con el servidor SQL, como mapa
    nombre => ip. Se usa el endpoint publico con firewall: por decision de
    alcance, el TFM no despliega red propia y reutiliza la existente.
    Obtener la IP actual con: curl -s https://api.ipify.org
  EOT
  type        = map(string)
  default     = {}
}

########################################
# Etiquetado
########################################

variable "tags" {
  description = "Etiquetas aplicadas a los recursos que crea el TFM."
  type        = map(string)
  default = {
    proyecto = "TFM-NTIC-Master"
    owner    = "brayan.sanchez@dataknow.co"
    gestion  = "terraform"
  }
}
