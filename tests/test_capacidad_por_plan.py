"""
Tests de la capacidad real por plan (modelo_prestow.CAPACIDAD_POR_PLAN),
agregada en la sesión del 22 de septiembre de 2026 — ver CLAUDE.md sección 6
("Capacidad real por plan") y docs/05_Estado_app_web.md sección 12.

Cubre capacidad_unidades() con y sin plan, la prioridad entre
CAPACIDAD_POR_PLAN/CAPACIDAD/aproximación por área, y la lectura del CSV de
overrides. No corre el modelo completo (eso se verificó a mano contra el
caso base, ver docs/05).
"""

import modelo_prestow as mp


def _limpiar_globales():
    """Los tests de este archivo tocan globales del módulo -- se restauran
    después de cada uno para no interferir con otros tests."""
    mp.CAPACIDAD = {}
    mp.CAPACIDAD_POR_PLAN = {}


def test_sin_datos_usa_aproximacion_por_area():
    _limpiar_globales()
    esperado = mp.AREA[(1, 1)] / mp.HUELLA["N_ALDEA_EKP"]
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP") == esperado
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP", t=5) == esperado


def test_capacidad_por_bodega_producto_sin_plan():
    _limpiar_globales()
    mp.CAPACIDAD = {(1, "N_ALDEA_EKP"): 200}
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP") == 200
    # Sin dato real por plan, un plan cualquiera cae al mismo valor
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP", t=7) == 200


def test_capacidad_por_plan_pisa_a_capacidad_por_bodega():
    _limpiar_globales()
    mp.CAPACIDAD = {(1, "N_ALDEA_EKP"): 200}
    mp.CAPACIDAD_POR_PLAN = {(1, 1, "N_ALDEA_EKP"): 194}
    # El plan con dato real usa ese valor, no el de CAPACIDAD
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP", t=1) == 194
    # Un plan sin dato real cae al valor por defecto de CAPACIDAD
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP", t=7) == 200
    # Sin especificar plan, nunca se consulta CAPACIDAD_POR_PLAN
    assert mp.capacidad_unidades(1, "N_ALDEA_EKP") == 200


def test_capacidad_por_plan_no_aplica_a_otro_producto_o_bodega():
    _limpiar_globales()
    mp.CAPACIDAD = {(4, "ARAUCO_BKP"): 435}
    mp.CAPACIDAD_POR_PLAN = {(4, 10, "ARAUCO_BKP"): 342}
    # Mismo plan, otro producto: no deberia pisar nada (no esta en el dict)
    assert mp.capacidad_unidades(4, "ARAUCO_EKP", t=10) == mp.AREA[(4, 1)] / mp.HUELLA["ARAUCO_EKP"]
    # Mismo producto, otra bodega: tampoco
    assert mp.capacidad_unidades(5, "ARAUCO_BKP", t=10) == mp.AREA[(5, 1)] / mp.HUELLA["ARAUCO_BKP"]
    # La combinacion exacta si pisa
    assert mp.capacidad_unidades(4, "ARAUCO_BKP", t=10) == 342


def test_cargar_capacidades_por_plan_archivo_inexistente(tmp_path):
    _limpiar_globales()
    ok = mp.cargar_capacidades_por_plan(str(tmp_path / "no_existe.csv"))
    assert ok is False
    assert mp.CAPACIDAD_POR_PLAN == {}


def test_cargar_capacidades_por_plan_lee_csv(tmp_path):
    _limpiar_globales()
    ruta = tmp_path / "capacidades_reales_por_plan.csv"
    ruta.write_text(
        "bodega,plan,producto,unidades_max_real\n"
        "1,1,N_ALDEA_EKP,194\n"
        "4,10,ARAUCO_BKP,342\n",
        encoding="utf-8",
    )
    ok = mp.cargar_capacidades_por_plan(str(ruta))
    assert ok is True
    assert mp.CAPACIDAD_POR_PLAN == {
        (1, 1, "N_ALDEA_EKP"): 194,
        (4, 10, "ARAUCO_BKP"): 342,
    }


def test_extraer_capacidades_reales_parsea_planes_en_espanol():
    """_parsear_planes() es la pieza mas fragil de extraer_capacidades_reales.py
    (texto libre en espanol de la planilla del puerto) -- se prueba aislada,
    sin depender del archivo raw real (no esta versionado)."""
    import extraer_capacidades_reales as ecr

    assert ecr._parsear_planes("PRIMER A SEXTO  PLAN") == [1, 2, 3, 4, 5, 6]
    assert ecr._parsear_planes("SEPTIMO Y OCTAVO PLAN") == [7, 8]
    assert ecr._parsear_planes("OCTAVO PLAN") == [8]
    assert ecr._parsear_planes("DECIMO Y UNDECIMO PLAN") == [10, 11]


def test_extraer_capacidades_reales_mapeo_producto_no_incluye_ambiguos():
    """Las entradas que mezclan 2 productos (ej. 'ARAUCO BKP / EKP') no
    deben tener mapeo -- eso es lo que hace que se descarten en extraer()."""
    import extraer_capacidades_reales as ecr

    assert "ARAUCO BKP / EKP" not in ecr.MAPEO_PRODUCTO
    assert "ARAUCO BKP EKP" not in ecr.MAPEO_PRODUCTO
    assert ecr.MAPEO_PRODUCTO["ARAUCO EKP"] == "ARAUCO_EKP"
    assert ecr.MAPEO_PRODUCTO["CELCO"] == "CELCO_UKP"
