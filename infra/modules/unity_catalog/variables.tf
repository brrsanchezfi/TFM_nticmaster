variable "catalog_suffix" {
  description = "Sufijo de aislamiento; produce bronze_<suffix>, silver_<suffix>, gold_<suffix>."
  type        = string
}

variable "use_cases" {
  description = "Schemas a crear dentro de cada catalogo (uno por caso de uso)."
  type        = list(string)
}

variable "owner" {
  description = "Propietario de catalogos y schemas."
  type        = string
}

variable "extra_readers" {
  description = "Principales con lectura sobre los catalogos."
  type        = list(string)
  default     = []
}

variable "storage_account_name" {
  description = "Cuenta ADLS Gen2 que respalda los contenedores por capa."
  type        = string
}

variable "managed_storage_prefix" {
  description = "Carpeta dentro de cada contenedor donde viven los datos gestionados del TFM."
  type        = string
}
