"""Entrypoint del Databricks Job: Landing -> Bronze (streaming).

Usa Auto Loader con trigger ``availableNow``: procesa todo lo pendiente en la
landing zone y termina, de modo que el job se comporta como una ejecución
acotada y no como un stream perpetuo. Así el cluster se apaga al acabar.
"""
from weather_events.pipeline import DEFAULT_CONFIG, build_engine


def main(config_path: str = DEFAULT_CONFIG) -> None:
    _, engine = build_engine(config_path)
    engine.run_streaming()


if __name__ == "__main__":
    main()
