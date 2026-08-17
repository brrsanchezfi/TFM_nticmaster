"""Entrypoint del Databricks Job: Landing -> Bronze (streaming).

Usa Auto Loader con trigger ``availableNow``: procesa todo lo pendiente en la
landing zone y termina, de modo que el job se comporta como una ejecución
acotada y no como un stream perpetuo. Así el cluster se apaga al acabar.
"""
from weather_events.pipeline import build_engine, parse_args


def main() -> None:
    args = parse_args()
    _, engine = build_engine(args.config, args.bundle_root)
    engine.run_streaming()


if __name__ == "__main__":
    main()
