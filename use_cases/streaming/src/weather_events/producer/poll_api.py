"""Job corto (job cluster efímero) que hace polling a la API pública de
clima (p.ej. Open-Meteo) y deposita JSON en la zona landing para que
Auto Loader los recoja. No requiere infraestructura de streaming
(Kafka/Event Hubs)."""


def main() -> None:
    raise NotImplementedError("Implementar polling a la API pública")


if __name__ == "__main__":
    main()
