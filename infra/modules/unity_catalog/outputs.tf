output "catalogs" {
  description = "Nombre del catalogo creado para cada capa."
  value       = { for layer, cat in databricks_catalog.layer : layer => cat.name }
}

output "schemas" {
  description = "Lista de schemas creados, en formato catalogo.schema."
  value = sort([
    for s in databricks_schema.use_case : "${s.catalog_name}.${s.name}"
  ])
}

output "storage_roots" {
  description = "Ruta ADLS que respalda cada catalogo."
  value       = local.storage_roots
}
