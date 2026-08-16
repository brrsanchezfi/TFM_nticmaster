"""Cableado de DKOps para el caso de uso streaming.

Única pieza de fontanería del bundle: construye el ``IngestionEngine`` a partir
de los contratos versionados en ``contracts/``. La lógica de ingesta y de
promoción vive en DKOps — aquí solo se resuelven rutas y se inyectan
dependencias.
"""
from __future__ import annotations

from pathlib import Path

from DKOps.ingestion.contracts import IngestionContractLoader
from DKOps.ingestion.engine import IngestionEngine
from DKOps.ingestion.ops import IngestionOpsLogger
from DKOps.launcher import Launcher

# .../use_cases/streaming/src/weather_events/pipeline.py -> .../use_cases/streaming
BUNDLE_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG = "config/config.dev.json"
OPS_PATH = "/tmp/weather_events/ops"

BRONZE_CONTRACTS = "contracts/ingestion/bronze"
SILVER_CONTRACTS = "contracts/ingestion/silver"


def _loader(contracts_dir: str, env) -> IngestionContractLoader:
    return IngestionContractLoader(
        contracts_dir=BUNDLE_ROOT / contracts_dir,
        base_dir=BUNDLE_ROOT,
        env=env,
    )


def build_engine(config_path: str = DEFAULT_CONFIG) -> tuple[Launcher, IngestionEngine]:
    """Devuelve el Launcher (dueño de la SparkSession) y el engine ya cableado."""
    launcher = Launcher(str(BUNDLE_ROOT / config_path))
    env = launcher.env

    bronze_loader = _loader(BRONZE_CONTRACTS, env)
    bronze_contracts = bronze_loader.load_all()
    bronze_tables = {c.name: bronze_loader.load_destination(c) for c in bronze_contracts}

    silver_loader = _loader(SILVER_CONTRACTS, env)
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
        ops=IngestionOpsLogger(launcher.spark, ops_path=OPS_PATH, pipeline="weather_events"),
    )
    return launcher, engine
