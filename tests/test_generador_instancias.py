"""Tests del generador de instancias de prueba (src/generador_instancias.py)."""

import generador_instancias as gen

BASE = "data/datos_entrada_kiwi_arrow.xlsx"


def test_caso_base_coincide_con_el_modelo():
    base = gen.leer_caso_base(BASE)
    assert base.tamano() == {"bodegas": 8, "destinos": 4, "productos": 5, "unidades": 29332}


def test_cada_instancia_tiene_pregunta_e_id_unico():
    instancias = gen.todas(BASE)
    ids = [i.id for i in instancias]
    assert len(ids) == len(set(ids))
    assert all("?" in i.proposito or i.grupo == "tamano" for i in instancias)


def test_dividir_destino_conserva_unidades_y_renumera_rotacion():
    base = gen.leer_caso_base(BASE)
    inst = gen.dividir_destino(base, "QINGDAO", "DESTINO_5", 0.5)
    assert inst.tamano()["unidades"] == 29332
    orden = {r["destino"]: r["orden_descarga"] for r in inst.rotacion}
    assert orden == {"TAICHUNG": 1, "QINGDAO": 2, "DESTINO_5": 3, "KUNSAN": 4, "ULSAN": 5}


def test_rendimiento_escala_el_tiempo_de_ciclo():
    base = gen.leer_caso_base(BASE)
    inst = gen.con_rendimientos(base, {1: 280})
    assert abs(inst.tiempo_ciclo_min[1] - 13.91 / 2) < 1e-9
    assert inst.tiempo_ciclo_min[2] == 7.16


def test_escribir_csv_lo_lee_el_modelo(tmp_path):
    import api

    inst = gen.instancias_de_prueba(gen.leer_caso_base(BASE))[6]  # P6, seis destinos
    gen.escribir_csv(inst, tmp_path)
    estado = api._guardar_globals()
    try:
        api._mp.cargar_datos(str(tmp_path))
        assert len(api._mp.DESTINOS) == 6
        assert sum(api._mp.DEMANDA.values()) == 29332
    finally:
        api._restaurar_globals(estado)
