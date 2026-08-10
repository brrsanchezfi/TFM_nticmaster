Notebooks delgados de orquestación: solo llaman a
`src/weather_events/jobs/*.py`. Toda la lógica real vive en `src/`, para que
sea testeable con pytest sin depender de un cluster.
