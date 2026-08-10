Notebooks delgados de orquestación: solo llaman a
`src/retail_sales/jobs/*.py`. Toda la lógica real vive en `src/`, para que
sea testeable con pytest sin depender de un cluster.
