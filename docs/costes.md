# Costes

## Qué genera coste

El trabajo no crea workspace, cuenta de almacenamiento ni warehouse. Los objetos
de Unity Catalog no tienen coste propio. El gasto viene de tres sitios:

| Partida | Quién la factura | Cómo se contiene |
|---|---|---|
| Job clusters | Databricks (DBUs) y Azure (máquinas virtuales) | Clusters efímeros de un solo nodo que se apagan al terminar el job |
| SQL Warehouse de los dashboards | Databricks | Se reutiliza el warehouse serverless del workspace, que se suspende a los 10 minutos |
| Almacenamiento | Azure | Unos pocos GB entre tablas, landing y logs |

En un cluster de un solo nodo la única máquina es el driver, y Azure exige que
sea bajo demanda. Por eso no hay ahorro por instancias spot.

El job de streaming tiene una programación cada 15 minutos, en pausa. Mientras
siga en pausa no consume nada fuera de las ejecuciones manuales.

## Consumo medido

Todos los job clusters llevan la etiqueta `proyecto=TFM-NTIC-Master`, declarada
en el bundle. A 16 de septiembre de 2026:

| Métrica | Valor |
|---|---|
| Periodo | 17 de agosto a 15 de septiembre de 2026 |
| Ejecuciones de job con consumo etiquetado | 65 |
| DBUs | 5,85 |
| Coste a precio de lista | 1,76 USD |

La cifra solo incluye lo que factura Databricks por los job clusters. No
incluye las máquinas virtuales, que factura Azure en la suscripción, ni el
warehouse de los dashboards, que es compartido y no lleva la etiqueta.

## Consultas

Consumo por día:

```sql
SELECT usage_date,
       ROUND(SUM(usage_quantity), 2) AS dbus
FROM system.billing.usage
WHERE custom_tags['proyecto'] = 'TFM-NTIC-Master'
GROUP BY usage_date
ORDER BY usage_date;
```

Total, ejecuciones y coste a precio de lista:

```sql
SELECT COUNT(DISTINCT u.usage_metadata.job_run_id) AS ejecuciones,
       ROUND(SUM(u.usage_quantity), 2) AS dbus,
       ROUND(SUM(u.usage_quantity * p.pricing.default), 2) AS usd
FROM system.billing.usage u
JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
 AND u.usage_start_time >= p.price_start_time
 AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.custom_tags['proyecto'] = 'TFM-NTIC-Master';
```

La parte de Azure se puede consultar en Cost Management filtrando por la misma
etiqueta, que Databricks propaga a las máquinas virtuales del cluster.
