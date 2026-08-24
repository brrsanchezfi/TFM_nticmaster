"""Tests del simulador del sistema origen — sin Spark."""
from customers.generators.simulate_changes import carga_inicial, lote_cambios


def test_la_carga_inicial_son_todo_altas():
    eventos = carga_inicial(50)
    assert {e["op_type"] for e in eventos} == {"I"}
    assert len({e["cliente_id"] for e in eventos}) == 50


def test_es_reproducible_con_la_misma_semilla():
    assert carga_inicial(20, semilla=3) == carga_inicial(20, semilla=3)


def test_el_lote_trae_los_tres_tipos_de_operacion():
    vigentes = carga_inicial(100)
    tipos = {e["op_type"] for e in lote_cambios(vigentes, semilla=5)}
    assert tipos == {"I", "U", "D"}


def test_las_altas_no_reutilizan_identificadores():
    """Si un alta reusara un cliente_id existente, el merge lo interpretaría
    como una modificación y se perdería el alta."""
    vigentes = carga_inicial(100)
    existentes = {c["cliente_id"] for c in vigentes}
    altas = {
        e["cliente_id"]
        for e in lote_cambios(vigentes, semilla=7)
        if e["op_type"] == "I"
    }
    assert not altas & existentes


def test_un_cliente_no_se_modifica_y_se_borra_en_el_mismo_lote():
    """Con dos eventos del mismo cliente y el mismo op_ts, el resultado
    dependería del orden de lectura."""
    vigentes = carga_inicial(100)
    eventos = lote_cambios(vigentes, semilla=11)

    modificados = {e["cliente_id"] for e in eventos if e["op_type"] == "U"}
    borrados = {e["cliente_id"] for e in eventos if e["op_type"] == "D"}
    assert not modificados & borrados


def test_los_updates_cambian_algo_de_verdad():
    """Un UPDATE que no modifica ningún campo no probaría nada."""
    vigentes = carga_inicial(100)
    original = {c["cliente_id"]: c for c in vigentes}

    updates = [e for e in lote_cambios(vigentes, semilla=13) if e["op_type"] == "U"]
    assert updates

    cambiados = [
        u for u in updates
        if any(u[campo] != original[u["cliente_id"]][campo]
               for campo in ("email", "ciudad", "segmento"))
    ]
    # Alguna modificación puede recaer en el mismo valor por azar, pero la
    # mayoría deben cambiar algo.
    assert len(cambiados) > len(updates) // 2


def test_todos_los_eventos_llevan_marca_temporal():
    for evento in lote_cambios(carga_inicial(50), semilla=17):
        assert evento["op_ts"]
