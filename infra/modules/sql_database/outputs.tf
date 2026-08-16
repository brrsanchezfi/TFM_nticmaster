output "server_fqdn" {
  description = "FQDN del servidor SQL."
  value       = azurerm_mssql_server.this.fully_qualified_domain_name
}

output "database_name" {
  description = "Nombre de la base de datos origen del caso CDC."
  value       = azurerm_mssql_database.this.name
}

output "jdbc_url" {
  description = "URL JDBC de conexion (autenticacion Entra ID)."
  value       = "jdbc:sqlserver://${azurerm_mssql_server.this.fully_qualified_domain_name}:1433;database=${azurerm_mssql_database.this.name};encrypt=true;trustServerCertificate=false"
}
