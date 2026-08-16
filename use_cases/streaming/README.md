# Caso de uso: streaming (weather_events)

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

    cd use_cases/streaming
    pip install -e ".[local]"
    pytest tests/unit -v

Toda la lógica de `src/weather_events/` se desarrolla y testea aquí, en local,
contra el config.local.json (DKOps en modo local, sin Databricks). Solo al
desplegar el bundle se apunta a config.dev.json (Databricks + Unity Catalog).
