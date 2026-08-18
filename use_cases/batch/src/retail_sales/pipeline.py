"""Cableado de DKOps para el caso de uso batch.

Única pieza de fontanería del bundle: construye el ``IngestionEngine`` a partir
de los contratos versionados en ``contracts/``. La lógica de ingesta y de
promoción vive en DKOps — aquí solo se resuelven rutas y se inyectan
dependencias.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from DKOps.ingestion.contracts import IngestionContractLoader
from DKOps.ingestion.engine import IngestionEngine
from DKOps.ingestion.ops import IngestionOpsLogger
from DKOps.launcher import Launcher

DEFAULT_CONFIG = "config/config.dev.json"

# Fallback solo para ejecución local: en Databricks /tmp vive en el driver y
# desaparece al apagarse el job cluster, así que el log de operaciones se
# perdería. En dev se resuelve contra el path 'ops' del config (ADLS).
OPS_PATH_FALLBACK = "/tmp/retail_sales/ops"

BRONZE_CONTRACTS = "contracts/ingestion/bronze"
SILVER_CONTRACTS = "contracts/ingestion/silver"


def resolve_bundle_root(bundle_root: str | None = None) -> Path:
    """Localiza la raíz del bundle, donde viven config/ y contracts/.

    El código se despliega como wheel, así que acaba en site-packages y no
    puede deducir la raíz desde ``__file__``: el job la pasa explícitamente
    (``${workspace.file_path}``). El resto de casos son para ejecución local.
    """
    if bundle_root:
        return Path(bundle_root)
    env = os.environ.get("BUNDLE_ROOT")
    if env:
        return Path(env)
    # Ejecución desde el repo: .../use_cases/batch/src/retail_sales/pipeline.py
    return Path(__file__).resolve().parents[2]


def build_engine(
    config_path: str = DEFAULT_CONFIG,
    bundle_root: str | None = None,
) -> tuple[Launcher, IngestionEngine]:
    """Devuelve el Launcher (dueño de la SparkSession) y el engine ya cableado."""
    root = resolve_bundle_root(bundle_root)
    launcher = Launcher(str(root / config_path))
    env = launcher.env

    def loader(contracts_dir: str) -> IngestionContractLoader:
        return IngestionContractLoader(
            contracts_dir=root / contracts_dir, base_dir=root, env=env
        )

    bronze_loader = loader(BRONZE_CONTRACTS)
    bronze_contracts = bronze_loader.load_all()
    bronze_tables = {c.name: bronze_loader.load_destination(c) for c in bronze_contracts}

    silver_loader = loader(SILVER_CONTRACTS)
    silver_contracts = silver_loader.load_all()
    silver_tables = {c.name: silver_loader.load_destination(c) for c in silver_contracts}

    # promote_silver() busca la tabla origen en bronze_tables, indexada por el
    # nombre del contrato o por el stem de source_contract_path. Se registran
    # ambas claves para que la resolución no dependa de cómo se nombren.
    for c in silver_contracts:
        src = silver_loader.load_source(c)
        if src is not None:
            bronze_tables.setdefault(c.name, src)
            bronze_tables.setdefault(Path(c.source_contract_path).stem, src)

    engine = IngestionEngine(
        spark=launcher.spark,
        env=env,
        bronze_contracts=bronze_contracts,
        silver_contracts=silver_contracts,
        bronze_tables=bronze_tables,
        silver_tables=silver_tables,
        ops=IngestionOpsLogger(
            launcher.spark,
            ops_path=env.get_path("ops") if env.has_path("ops") else OPS_PATH_FALLBACK,
            pipeline="retail_sales",
        ),
    )
    return launcher, engine


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos comunes a todos los entrypoints del bundle."""
    p = argparse.ArgumentParser()
    p.add_argument("--bundle-root", default=None,
                   help="Raíz del bundle desplegado (workspace.file_path).")
    p.add_argument("--config", default=DEFAULT_CONFIG,
                   help="Ruta del config.json, relativa a la raíz del bundle.")
    return p.parse_known_args(argv)[0]
