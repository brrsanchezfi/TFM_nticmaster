"""Las cinco dimensiones del modelo, con datos fijos escritos a mano.

A diferencia de las ventas, que se generan con una semilla y cambian en cada
lote, una dimensión es un catálogo: cambia poco y su contenido es conocido. Por
eso van escritas a mano en lugar de sintetizadas.

Que el contenido sea siempre el mismo es la propiedad que hace demostrable la
recarga completa: se puede ejecutar el job cien veces y comprobar que la tabla
queda idéntica, sin filas duplicadas ni versiones sueltas.

Los volúmenes son deliberadamente distintos —de 4 a 20 filas— para que se vea
que el mismo job procesa tablas de tamaños diferentes en una sola pasada.
"""
from __future__ import annotations

# ── dim_canal ──────────────────────────────────────────────────────────────
# La más pequeña. Un catálogo que no crece.
CANALES = [
    ("CAN-01", "online",    "digital",  True),
    ("CAN-02", "tienda",    "fisico",   True),
    ("CAN-03", "telefono",  "asistido", True),
    ("CAN-04", "catalogo",  "asistido", False),   # descatalogado
]
COLUMNAS_CANAL = ["canal_id", "canal", "tipo", "activo"]


# ── dim_ciudad ─────────────────────────────────────────────────────────────
CIUDADES = [
    ("CIU-01", "Madrid",     "Comunidad de Madrid", "España",   3223000),
    ("CIU-02", "Barcelona",  "Cataluña",            "España",   1620000),
    ("CIU-03", "Valencia",   "Comunidad Valenciana", "España",   789000),
    ("CIU-04", "Sevilla",    "Andalucía",           "España",    684000),
    ("CIU-05", "Bilbao",     "País Vasco",          "España",    346000),
    ("CIU-06", "Zaragoza",   "Aragón",              "España",    675000),
    ("CIU-07", "Bogotá",     "Cundinamarca",        "Colombia", 7900000),
    ("CIU-08", "Medellín",   "Antioquia",           "Colombia", 2530000),
]
COLUMNAS_CIUDAD = ["ciudad_id", "ciudad", "region", "pais", "habitantes"]


# ── dim_categoria ──────────────────────────────────────────────────────────
CATEGORIAS = [
    ("CAT-01", "Hogar",       "Bazar",       21.0),
    ("CAT-02", "Textil",      "Moda",        21.0),
    ("CAT-03", "Electronica", "Tecnología",  21.0),
    ("CAT-04", "Deporte",     "Ocio",        21.0),
    ("CAT-05", "Libros",      "Cultura",      4.0),   # IVA reducido
    ("CAT-06", "Alimentacion", "Consumo",    10.0),
]
COLUMNAS_CATEGORIA = ["categoria_id", "categoria", "familia", "iva"]


# ── dim_producto ───────────────────────────────────────────────────────────
PRODUCTOS = [
    ("PRD-001", "Lámpara de mesa",     "CAT-01", "Hogar",        24.90, True),
    ("PRD-002", "Juego de sábanas",    "CAT-01", "Hogar",        39.90, True),
    ("PRD-003", "Cafetera italiana",   "CAT-01", "Hogar",        18.50, True),
    ("PRD-004", "Camiseta básica",     "CAT-02", "Textil",        9.90, True),
    ("PRD-005", "Pantalón vaquero",    "CAT-02", "Textil",       45.00, True),
    ("PRD-006", "Chaqueta de punto",   "CAT-02", "Textil",       59.90, False),
    ("PRD-007", "Auriculares",         "CAT-03", "Electronica",  79.00, True),
    ("PRD-008", "Teclado mecánico",    "CAT-03", "Electronica",  99.90, True),
    ("PRD-009", "Zapatillas running",  "CAT-04", "Deporte",      74.50, True),
    ("PRD-010", "Esterilla de yoga",   "CAT-04", "Deporte",      22.00, True),
    ("PRD-011", "Novela de bolsillo",  "CAT-05", "Libros",        9.95, True),
    ("PRD-012", "Café en grano 1kg",   "CAT-06", "Alimentacion", 15.75, True),
]
COLUMNAS_PRODUCTO = [
    "producto_id", "producto", "categoria_id", "categoria",
    "precio_unitario", "activo",
]


# ── dim_cliente ────────────────────────────────────────────────────────────
# La más grande de las cinco, y la que tendría sentido llevar con SCD Tipo 2:
# la ciudad y el segmento de un cliente cambian con el tiempo, y hoy esos
# cambios se pierden al recargar. Ver la nota en la documentación del caso.
CLIENTES = [
    ("CLI-001", "Ana Ruiz",         "CIU-01", "Madrid",    "premium", "2024-01-15"),
    ("CLI-002", "Luis Ferrer",      "CIU-01", "Madrid",    "retail",  "2024-02-03"),
    ("CLI-003", "Marta Sanz",       "CIU-02", "Barcelona", "premium", "2024-02-19"),
    ("CLI-004", "Jorge Iglesias",   "CIU-02", "Barcelona", "retail",  "2024-03-07"),
    ("CLI-005", "Elena Cortés",     "CIU-03", "Valencia",  "retail",  "2024-03-22"),
    ("CLI-006", "Pablo Nieto",      "CIU-03", "Valencia",  "premium", "2024-04-11"),
    ("CLI-007", "Rocío Vega",       "CIU-04", "Sevilla",   "retail",  "2024-05-02"),
    ("CLI-008", "Andrés Lobo",      "CIU-04", "Sevilla",   "retail",  "2024-05-28"),
    ("CLI-009", "Nerea Ibarra",     "CIU-05", "Bilbao",    "premium", "2024-06-14"),
    ("CLI-010", "Gorka Etxeberria", "CIU-05", "Bilbao",    "retail",  "2024-07-01"),
    ("CLI-011", "Silvia Marco",     "CIU-06", "Zaragoza",  "retail",  "2024-07-19"),
    ("CLI-012", "Raúl Benito",      "CIU-06", "Zaragoza",  "premium", "2024-08-05"),
    ("CLI-013", "Camila Torres",    "CIU-07", "Bogotá",    "premium", "2024-08-23"),
    ("CLI-014", "Julián Osorio",    "CIU-07", "Bogotá",    "retail",  "2024-09-09"),
    ("CLI-015", "Valeria Restrepo", "CIU-08", "Medellín",  "retail",  "2024-09-30"),
    ("CLI-016", "Mateo Zapata",     "CIU-08", "Medellín",  "premium", "2024-10-17"),
    ("CLI-017", "Irene Pardo",      "CIU-01", "Madrid",    "retail",  "2024-11-04"),
    ("CLI-018", "Hugo Salas",       "CIU-02", "Barcelona", "retail",  "2024-11-25"),
    ("CLI-019", "Lucía Ortega",     "CIU-03", "Valencia",  "premium", "2024-12-12"),
    ("CLI-020", "Diego Arana",      "CIU-05", "Bilbao",    "retail",  "2025-01-08"),
]
COLUMNAS_CLIENTE = [
    "cliente_id", "nombre", "ciudad_id", "ciudad", "segmento", "fecha_alta",
]


# Lo que consume el job: nombre de la dimensión → (filas, columnas).
# El orden es el de carga, de la más pequeña a la más grande, para que el log
# lea de forma natural.
DIMENSIONES: dict[str, tuple[list[tuple], list[str]]] = {
    "dim_canal":     (CANALES,    COLUMNAS_CANAL),
    "dim_categoria": (CATEGORIAS, COLUMNAS_CATEGORIA),
    "dim_ciudad":    (CIUDADES,   COLUMNAS_CIUDAD),
    "dim_producto":  (PRODUCTOS,  COLUMNAS_PRODUCTO),
    "dim_cliente":   (CLIENTES,   COLUMNAS_CLIENTE),
}
