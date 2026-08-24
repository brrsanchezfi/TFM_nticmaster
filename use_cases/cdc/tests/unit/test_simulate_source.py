"""Tests del contrato de datos que emite el simulador hacia la landing."""
from customers.generators.simulate_changes import carga_inicial, lote_cambios
from customers.jobs.simulate_source import CAMPOS_ORIGEN

CAMPOS_EVENTO = set(CAMPOS_ORIGEN) | {"op_type", "op_ts"}

# Columnas internas de Silver que jamás deben viajar de vuelta a la landing.
COLUMNAS_INTERNAS = {"is_deleted", "_silver_modified_at", "_ingested_at",
                     "_ingested_date", "_source_file"}


def test_la_carga_inicial_emite_solo_campos_del_origen():
    for evento in carga_inicial(20):
        assert set(evento) == CAMPOS_EVENTO


def test_el_lote_emite_solo_campos_del_origen():
    """Regresión: el simulador leía los clientes vigentes de Silver y devolvía
    sus filas tal cual, arrastrando is_deleted y _silver_modified_at hasta la
    landing. Auto Loader los detectaba como campos nuevos y abortaba el stream
    con UNKNOWN_FIELD_EXCEPTION."""
    vigentes = carga_inicial(50)
    for evento in lote_cambios(vigentes, semilla=3):
        assert set(evento) == CAMPOS_EVENTO


def test_ninguna_columna_interna_se_filtra_a_la_landing():
    vigentes = carga_inicial(50)
    # Simula lo que devolvería Silver si no se proyectaran los campos
    contaminados = [
        {**c, "is_deleted": False, "_silver_modified_at": "2026-08-24T00:00:00"}
        for c in vigentes
    ]
    proyectados = [{k: c[k] for k in CAMPOS_ORIGEN} for c in contaminados]

    for evento in lote_cambios(proyectados, semilla=5):
        assert not (set(evento) & COLUMNAS_INTERNAS)
