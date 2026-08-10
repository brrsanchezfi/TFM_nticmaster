#!/usr/bin/env bash
# =============================================================================
# bootstrap_repo.sh
#
# Crea el esqueleto completo del repositorio TFM_nticmaster: carpetas,
# READMEs de responsabilidad, y estructura modular "tipo software" para
# cada caso de uso (batch / streaming / cdc / cdf), cada uno con su propio
# paquete Python de dominio (para poder testearse offline con DKOps antes
# de tocar Databricks).
#
# Uso:
#   chmod +x scripts/bootstrap_repo.sh
#   ./scripts/bootstrap_repo.sh
#
# Pensado para ejecutarse dentro de WSL, en la raíz del repo ya clonado,
# idealmente en una rama feat/repo-scaffold.
# =============================================================================
set -euo pipefail

# --- Nombres de dominio de negocio por caso de uso (renombrables) ----------
BATCH_DOMAIN="retail_sales"        # batch: ventas/catálogo sintético
STREAMING_DOMAIN="weather_events"  # streaming: clima vía API pública (Open-Meteo)
CDC_DOMAIN="customers"             # cdc: clientes simulados en Azure SQL
CDF_DOMAIN="orders"                # cdf: pedidos con Change Data Feed

ROOT="$(pwd)"
echo "Creando estructura en: ${ROOT}"

mkfile() {
  # mkfile <path> <<'EOF' ... EOF   -> no sobreescribe si ya existe
  local path="$1"
  if [ -f "$path" ]; then
    echo "  (ya existe, no se toca) $path"
    cat > /dev/null
  else
    mkdir -p "$(dirname "$path")"
    cat > "$path"
    echo "  creado: $path"
  fi
}

gitkeep() {
  mkdir -p "$1"
  [ -f "$1/.gitkeep" ] || touch "$1/.gitkeep"
}

# =============================================================================
# 1. Raíz del repo
# =============================================================================
mkfile "README.md" <<'EOF'
# TFM_nticmaster

PoC End-to-End de ingeniería de datos sobre Databricks/Azure, construida con
Databricks Asset Bundles y la librería DKOps (https://github.com/brrsanchezfi/DKOps).

Ver `docs/` para la memoria completa (arquitectura, casos de uso, costes).

## Estructura

- `docs/`        Memoria del TFM (MkDocs)
- `infra/`       Infraestructura Azure como código (Terraform) — práctica adicional
- `platform/`    Piezas compartidas entre casos de uso (versión de DKOps, etc.)
- `use_cases/`   Un caso de uso por patrón de ingesta: batch, streaming, cdc, cdf
- `scripts/`     Utilidades de desarrollo local
- `.github/workflows/` CI/CD

## Desarrollo local

Cada caso de uso en `use_cases/<patron>/` es un paquete Python independiente
que se puede instalar y testear 100% offline (sin Databricks) gracias al modo
local de DKOps. Ver el README de cada caso de uso para el detalle.
EOF

mkfile ".gitignore" <<'EOF'
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Databricks
.databricks/
.databricks-login.json

# Terraform
**/.terraform/
*.tfstate
*.tfstate.backup
*.tfvars

# OS / editores
.DS_Store
.vscode/
.idea/

# Datos locales de prueba
/tmp/
**/data/local/*
!**/data/local/.gitkeep
EOF

mkfile "CHANGELOG.md" <<'EOF'
# Changelog

## [Unreleased]
- Scaffolding inicial del repositorio.
EOF

# =============================================================================
# 2. docs/ — Memoria del TFM (MkDocs)
# =============================================================================
mkfile "docs/mkdocs.yml" <<'EOF'
site_name: TFM NTIC Master - PoC Databricks
nav:
  - Inicio: index.md
  - Arquitectura:
      - Global: arquitectura/global.md
      - Lakehouse: arquitectura/lakehouse.md
      - Unity Catalog: arquitectura/unity-catalog.md
  - Casos de uso:
      - Batch: casos_uso/batch.md
      - Streaming: casos_uso/streaming.md
      - CDC: casos_uso/cdc.md
      - CDF: casos_uso/cdf.md
  - Stack (incl. DKOps): stack.md
  - Infraestructura: infraestructura.md
  - Costes: costes.md
  - CI/CD: ci-cd.md
  - Conclusiones: conclusiones.md
theme:
  name: material
EOF

mkfile "docs/index.md" <<'EOF'
# TFM NTIC Master — PoC de ingeniería de datos sobre Databricks/Azure

Objetivo, alcance y cómo navegar esta documentación.
EOF

for f in arquitectura/global arquitectura/lakehouse arquitectura/unity-catalog \
         casos_uso/batch casos_uso/streaming casos_uso/cdc casos_uso/cdf \
         stack infraestructura costes ci-cd conclusiones; do
  mkfile "docs/${f}.md" <<EOF
# $(basename "$f")

_Pendiente de redactar._
EOF
done

# =============================================================================
# 3. infra/ — Terraform (práctica adicional, IaC)
# =============================================================================
gitkeep "infra/envs/dev"
gitkeep "infra/modules/resource_group"
gitkeep "infra/modules/storage"
gitkeep "infra/modules/databricks_workspace"
gitkeep "infra/modules/unity_catalog"
gitkeep "infra/modules/sql_database"
gitkeep "infra/modules/networking"

mkfile "infra/README.md" <<'EOF'
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
EOF

# =============================================================================
# 4. platform/ — piezas compartidas entre casos de uso
# =============================================================================
mkfile "platform/dkops_version.txt" <<'EOF'
# Versión/tag de DKOps usada en todos los casos de uso.
# Fijar un tag o commit concreto, no "main", para reproducibilidad.
# Ejemplo: git+https://github.com/brrsanchezfi/DKOps.git@v0.3.0
EOF

mkfile "platform/README.md" <<'EOF'
# Platform

Recursos compartidos entre los 4 casos de uso: versión pineada de DKOps
y cualquier convención común (nombres de catálogos, esquema de config).
No contiene lógica de negocio.
EOF

# =============================================================================
# 5. use_cases/ — un paquete "tipo software" por caso de uso
# =============================================================================
scaffold_use_case() {
  local pattern="$1"     # batch | streaming | cdc | cdf
  local domain="$2"      # nombre del paquete de dominio, ej. weather_events
  local base="use_cases/${pattern}"

  mkfile "${base}/README.md" <<EOF
# Caso de uso: ${pattern} (${domain})

1. Problema
2. Objetivo
3. Fuente de datos
4. Arquitectura
5. Flujo de datos
6. Componentes
7. Implementación
8. Uso de DKOps
9. Despliegue
10. Ejecución
11. Resultado
12. Coste
13. Limitaciones

## Desarrollo local (offline)

    cd use_cases/${pattern}
    pip install -e ".[local]"
    pytest tests/unit -v

Toda la lógica de \`src/${domain}/\` se desarrolla y testea aquí, en local,
contra el config.local.json (DKOps en modo local, sin Databricks). Solo al
desplegar el bundle se apunta a config.dev.json (Databricks + Unity Catalog).
EOF

  mkfile "${base}/databricks.yml" <<EOF
bundle:
  name: tfm_${pattern}_${domain}

include:
  - resources/*.yml

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: \${var.databricks_host}
EOF

  mkfile "${base}/pyproject.toml" <<EOF
[project]
name = "${domain}"
version = "0.1.0"
description = "Caso de uso ${pattern} — dominio ${domain}"
dependencies = [
  # Fijar tag/commit concreto, ver platform/dkops_version.txt
  "dkops @ git+https://github.com/brrsanchezfi/DKOps.git@<tag>",
]

[project.optional-dependencies]
local = ["pyspark>=3.5", "delta-spark>=3.2", "pytest"]
EOF

  mkfile "${base}/config/config.local.json" <<EOF
{
  "EXECUTION_ENVIRONMENT": "local",
  "SPARK_APP_NAME": "${domain}-local",
  "environments": {
    "local": {
      "env": "local",
      "env_short": "l",
      "catalogs": { "bronze": "bronze", "silver": "silver", "gold": "gold" },
      "paths": {
        "landing": "/tmp/${domain}/landing",
        "bronze": "/tmp/${domain}/bronze",
        "silver": "/tmp/${domain}/silver",
        "gold": "/tmp/${domain}/gold",
        "checkpoint": "/tmp/${domain}/checkpoints",
        "ops": "/tmp/${domain}/ops"
      }
    }
  }
}
EOF

  mkfile "${base}/config/config.dev.json" <<EOF
{
  "EXECUTION_ENVIRONMENT": "databricks",
  "SPARK_APP_NAME": "${domain}-dev",
  "environments": {
    "dev": {
      "env": "dev",
      "env_short": "d",
      "catalogs": { "bronze": "bronze", "silver": "silver", "gold": "gold" }
    }
  }
}
EOF

  gitkeep "${base}/contracts/ingestion/bronze"
  gitkeep "${base}/contracts/ingestion/silver"
  gitkeep "${base}/contracts/tables/bronze"
  gitkeep "${base}/contracts/tables/silver"
  gitkeep "${base}/contracts/tables/gold"

  mkfile "${base}/src/${domain}/__init__.py" <<'EOF'
EOF
  mkfile "${base}/src/${domain}/jobs/__init__.py" <<'EOF'
EOF
  mkfile "${base}/src/${domain}/jobs/ingest_bronze.py" <<EOF
"""Entrypoint invocado por el Databricks Job: Landing -> Bronze."""
from dkops.launcher import Launcher
from dkops.ingestion.engine import IngestionEngine


def main(config_path: str = "config/config.dev.json") -> None:
    launcher = Launcher(config_path)
    engine = IngestionEngine.from_spark(
        spark=launcher.spark,
        env=launcher.env,
        bronze_contracts_dir="contracts/ingestion/bronze",
        silver_contracts_dir="contracts/ingestion/silver",
        tables_base_dir="contracts/tables",
        ops_path="/tmp/${domain}/ops",
    )
    engine.ingest_bronze()


if __name__ == "__main__":
    main()
EOF
  mkfile "${base}/src/${domain}/jobs/promote_silver.py" <<EOF
"""Entrypoint invocado por el Databricks Job: Bronze -> Silver."""
from dkops.launcher import Launcher
from dkops.ingestion.engine import IngestionEngine


def main(config_path: str = "config/config.dev.json") -> None:
    launcher = Launcher(config_path)
    engine = IngestionEngine.from_spark(
        spark=launcher.spark,
        env=launcher.env,
        bronze_contracts_dir="contracts/ingestion/bronze",
        silver_contracts_dir="contracts/ingestion/silver",
        tables_base_dir="contracts/tables",
        ops_path="/tmp/${domain}/ops",
    )
    engine.promote_silver()


if __name__ == "__main__":
    main()
EOF
  mkfile "${base}/src/${domain}/jobs/build_gold.py" <<EOF
"""Entrypoint invocado por el Databricks Job: Silver -> Gold.

La lógica de negocio específica del dominio (agregaciones, KPIs) vive en
transformations/, no aquí — este módulo solo orquesta.
"""
from ${domain}.transformations import gold_metrics


def main() -> None:
    gold_metrics.build()


if __name__ == "__main__":
    main()
EOF

  mkfile "${base}/src/${domain}/transformations/__init__.py" <<'EOF'
EOF
  mkfile "${base}/src/${domain}/transformations/gold_metrics.py" <<EOF
"""Lógica de negocio del dominio '${domain}' para construir la capa Gold.

Esta es la parte específica de ESTE caso de uso (no genérica de DKOps):
aquí van las reglas de negocio, agregaciones y métricas concretas del
dominio ${domain}.
"""


def build() -> None:
    raise NotImplementedError("Definir agregaciones de negocio de ${domain}")
EOF

  gitkeep "${base}/src/${domain}/utils"

  mkfile "${base}/resources/jobs.yml" <<EOF
resources:
  jobs:
    ${domain}_pipeline:
      name: "${pattern}_${domain}_pipeline"
      tasks:
        - task_key: ingest_bronze
          python_wheel_task:
            entry_point: main
            package_name: ${domain}
        - task_key: promote_silver
          depends_on:
            - task_key: ingest_bronze
          python_wheel_task:
            entry_point: main
            package_name: ${domain}
        - task_key: build_gold
          depends_on:
            - task_key: promote_silver
          python_wheel_task:
            entry_point: main
            package_name: ${domain}
EOF

  gitkeep "${base}/tests/unit"
  gitkeep "${base}/tests/fixtures"
  mkfile "${base}/tests/unit/test_gold_metrics.py" <<EOF
"""Tests unitarios offline — no requieren Databricks, solo Spark local
(instalado vía DKOps modo local)."""
import pytest


def test_placeholder():
    pytest.skip("Implementar tests de ${domain} en fase de desarrollo")
EOF

  gitkeep "${base}/notebooks"
  mkfile "${base}/notebooks/README.md" <<EOF
Notebooks delgados de orquestación: solo llaman a
\`src/${domain}/jobs/*.py\`. Toda la lógica real vive en \`src/\`, para que
sea testeable con pytest sin depender de un cluster.
EOF
}

scaffold_use_case "batch"     "${BATCH_DOMAIN}"
scaffold_use_case "streaming" "${STREAMING_DOMAIN}"
scaffold_use_case "cdc"       "${CDC_DOMAIN}"
scaffold_use_case "cdf"       "${CDF_DOMAIN}"

# --- Extras específicos de streaming (productor) y cdc (generador) ---------
gitkeep "use_cases/streaming/src/${STREAMING_DOMAIN}/producer"
mkfile "use_cases/streaming/src/${STREAMING_DOMAIN}/producer/poll_api.py" <<EOF
"""Job corto (job cluster efímero) que hace polling a la API pública de
clima (p.ej. Open-Meteo) y deposita JSON en la zona landing para que
Auto Loader los recoja. No requiere infraestructura de streaming
(Kafka/Event Hubs)."""


def main() -> None:
    raise NotImplementedError("Implementar polling a la API pública")


if __name__ == "__main__":
    main()
EOF

gitkeep "use_cases/cdc/src/${CDC_DOMAIN}/generators"
mkfile "use_cases/cdc/src/${CDC_DOMAIN}/generators/simulate_changes.py" <<EOF
"""Genera datos sintéticos (Faker) y simula INSERT/UPDATE/DELETE en la
tabla de Azure SQL usada como origen del caso de uso CDC."""


def main() -> None:
    raise NotImplementedError("Implementar simulador de cambios en Azure SQL")


if __name__ == "__main__":
    main()
EOF

# =============================================================================
# 6. scripts/ y CI/CD
# =============================================================================
mkfile "scripts/bootstrap_repo.sh" <<'PLACEHOLDER'
# Este mismo script vive aquí una vez ejecutado la primera vez.
PLACEHOLDER

mkfile "scripts/deploy_all.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
for uc in batch streaming cdc cdf; do
  echo "== Desplegando bundle: $uc =="
  (cd "use_cases/$uc" && databricks bundle deploy -t dev)
done
EOF

mkfile "scripts/teardown.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "Destruye infraestructura no persistente (uso manual y cuidadoso)."
# cd infra/envs/dev && terraform destroy
EOF

gitkeep ".github/workflows"
mkfile ".github/workflows/infra-plan-apply.yml" <<'EOF'
name: infra-plan-apply
on:
  pull_request:
    paths: ["infra/**"]
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "TODO: terraform init && terraform plan"
EOF

for uc in batch streaming cdc cdf; do
  mkfile ".github/workflows/${uc}-ci.yml" <<EOF
name: ${uc}-ci
on:
  pull_request:
    paths: ["use_cases/${uc}/**"]
jobs:
  test-and-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "TODO: pip install -e .[local] && pytest && databricks bundle validate"
EOF
done

echo ""
echo "Scaffolding completado."
echo "Revisa con: find . -not -path '*/.git/*' | sort"
