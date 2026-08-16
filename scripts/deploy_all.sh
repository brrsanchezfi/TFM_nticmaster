#!/usr/bin/env bash
set -euo pipefail
for uc in batch streaming cdc cdf; do
  echo "== Desplegando bundle: $uc =="
  (cd "use_cases/$uc" && databricks bundle deploy -t dev)
done
