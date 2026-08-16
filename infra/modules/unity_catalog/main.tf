terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.50"
    }
  }
}

locals {
  layers = ["bronze", "silver", "gold"]

  # bronze => bronze_tfm, silver => silver_tfm, gold => gold_tfm
  catalog_names = {
    for layer in local.layers :
    layer => "${layer}_${var.catalog_suffix}"
  }

  # Cada capa se apoya en el contenedor homonimo que ya existe en la cuenta,
  # bajo una carpeta propia del TFM para no mezclarse con los datos de trabajo.
  storage_roots = {
    for layer in local.layers :
    layer => "abfss://${layer}@${var.storage_account_name}.dfs.core.windows.net/${var.managed_storage_prefix}"
  }

  # Producto cartesiano capa x caso de uso: bronze/batch, bronze/streaming, ...
  schemas = {
    for pair in setproduct(local.layers, var.use_cases) :
    "${pair[0]}_${pair[1]}" => {
      layer    = pair[0]
      use_case = pair[1]
    }
  }

  catalog_reader_grants = {
    for pair in setproduct(local.layers, var.extra_readers) :
    "${pair[0]}_${pair[1]}" => {
      layer     = pair[0]
      principal = pair[1]
    }
  }
}

resource "databricks_catalog" "layer" {
  for_each = local.catalog_names

  name         = each.value
  storage_root = local.storage_roots[each.key]
  owner        = var.owner
  comment      = "TFM NTIC Master - capa ${each.key} del lakehouse."

  properties = {
    proyecto = "TFM-NTIC-Master"
    capa     = each.key
  }

  # Sin force_destroy: un destroy no debe poder borrar datos por accidente.
  # Para desmontar el TFM al terminar, vaciar los catalogos a mano primero.
}

resource "databricks_schema" "use_case" {
  for_each = local.schemas

  catalog_name = databricks_catalog.layer[each.value.layer].name
  name         = each.value.use_case
  owner        = var.owner
  comment      = "Caso de uso ${each.value.use_case} en la capa ${each.value.layer}."

  properties = {
    caso_uso = each.value.use_case
  }
}

resource "databricks_grants" "catalog_readers" {
  for_each = length(var.extra_readers) > 0 ? local.catalog_names : {}

  catalog = databricks_catalog.layer[each.key].name

  dynamic "grant" {
    for_each = var.extra_readers
    content {
      principal  = grant.value
      privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
    }
  }
}
