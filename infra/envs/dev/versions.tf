terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.50"
    }
  }

  # State local: la PoC la despliega una sola persona desde su maquina.
  # Si en algun momento se comparte, mover a un backend remoto (azurerm)
  # apuntando a un contenedor propio del TFM.
  backend "local" {
    path = "terraform.tfstate"
  }
}
