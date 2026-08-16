provider "azurerm" {
  features {}

  subscription_id = var.subscription_id

  # El provider no debe intentar registrar providers a nivel de suscripcion:
  # la cuenta que ejecuta este codigo es Contributor solo del Resource Group.
  resource_provider_registrations = "none"
}

# Autenticacion contra el workspace via Azure CLI (az login).
provider "databricks" {
  host                        = var.databricks_host
  azure_workspace_resource_id = data.azurerm_databricks_workspace.this.id
}
