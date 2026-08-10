# Infraestructura (Terraform)

Aprovisiona los recursos base en Azure: Resource Group, ADLS Gen2,
Databricks Workspace (vinculado al metastore de Unity Catalog existente),
catálogos/schemas de Unity Catalog, y Azure SQL Database (serverless) para
el caso de uso CDC.

Esto es una práctica adicional de buenas prácticas (IaC), no un objetivo
evaluable central del TFM — si en algún momento falta tiempo, algún recurso
puntual puede crearse manualmente sin comprometer el resultado.

## Uso

    cd infra/envs/dev
    terraform init
    terraform plan
    terraform apply
