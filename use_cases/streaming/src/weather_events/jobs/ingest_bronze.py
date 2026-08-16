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
        ops_path="/tmp/weather_events/ops",
    )
    engine.ingest_bronze()


if __name__ == "__main__":
    main()
