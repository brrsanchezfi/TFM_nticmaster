"""Cableado del caso de uso CDF.

A diferencia de los casos batch/streaming/cdc, aquí no hay ingesta desde una
landing zone: el origen es una tabla Delta que ya vive en Silver. Por eso este
módulo no construye un ``IngestionEngine`` — lo que necesita el caso es
resolver contratos de tabla y la SparkSession.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from DKOps.launcher import Launcher
from DKOps.table_governance import TableContract, load_contract

DEFAULT_CONFIG = "config/config.dev.json"

CONTRATO_ORIGEN = "contracts/tables/silver/pedidos.json"
CONTRATO_AGREGADO = "contracts/tables/gold/pedidos_agregado.json"
CONTRATO_CONTROL = "contracts/tables/gold/cdf_control.json"


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
    return Path(__file__).resolve().parents[2]


def build_context(
    config_path: str = DEFAULT_CONFIG,
    bundle_root: str | None = None,
) -> tuple[Launcher, Path]:
    """Arranca el Launcher de DKOps y devuelve también la raíz del bundle."""
    root = resolve_bundle_root(bundle_root)
    return Launcher(str(root / config_path)), root


def contratos(root: Path, env) -> dict[str, TableContract]:
    """Carga los tres contratos de tabla del caso."""
    return {
        "origen": load_contract(root / CONTRATO_ORIGEN, env=env),
        "agregado": load_contract(root / CONTRATO_AGREGADO, env=env),
        "control": load_contract(root / CONTRATO_CONTROL, env=env),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos comunes a todos los entrypoints del bundle."""
    p = argparse.ArgumentParser()
    p.add_argument("--bundle-root", default=None,
                   help="Raíz del bundle desplegado (workspace.file_path).")
    p.add_argument("--config", default=DEFAULT_CONFIG,
                   help="Ruta del config.json, relativa a la raíz del bundle.")
    p.add_argument("--lote", type=int, default=0,
                   help="Semilla del lote de cambios. 0 (por defecto) la deriva "
                        "de la versión actual de la tabla, de modo que cada "
                        "ejecución genera cambios distintos. Un valor explícito "
                        "hace el lote reproducible.")
    return p.parse_known_args(argv)[0]
