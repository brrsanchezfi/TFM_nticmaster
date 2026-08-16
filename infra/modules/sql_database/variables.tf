variable "resource_group_name" {
  description = "Resource Group existente donde se crea el servidor SQL."
  type        = string
}

variable "location" {
  description = "Region del Resource Group."
  type        = string
}

variable "server_name" {
  description = "Nombre del servidor logico (unico a nivel global)."
  type        = string
}

variable "database_name" {
  description = "Nombre de la base de datos origen del caso de uso CDC."
  type        = string
}

variable "entra_admin_login" {
  description = "UPN del administrador Entra ID del servidor."
  type        = string
}

variable "entra_admin_object_id" {
  description = "Object ID en Entra ID del administrador del servidor."
  type        = string
}

variable "allowed_ips" {
  description = "Mapa nombre => IP publica autorizada en el firewall del servidor."
  type        = map(string)
  default     = {}
}

variable "auto_pause_delay_in_minutes" {
  description = "Minutos de inactividad antes de pausar la base. 60 es el minimo admitido."
  type        = number
  default     = 60
}

variable "min_capacity" {
  description = "vCores minimos en serverless."
  type        = number
  default     = 0.5
}

variable "max_size_gb" {
  description = "Tamaño maximo de la base de datos."
  type        = number
  default     = 2
}

variable "tags" {
  description = "Etiquetas del recurso."
  type        = map(string)
  default     = {}
}
