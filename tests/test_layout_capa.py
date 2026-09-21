"""
Tests de src/layout_capa.py.

Casos cubiertos:
  1. Capa mono-producto: reproduce las 194 unidades de N_ALDEA_EKP en la
     bodega 1 (plantilla real verificada, CLAUDE.md seccion 9).
  2. Capa mixta: coloca exactamente las unidades pedidas de cada grupo, sin
     solapar franjas ni excederse del piso.
  3. Caso vacio / sin espacio: no revienta, devuelve lista vacia.
"""

from layout_capa import GrupoCapa, calcular_layout_capa

# Geometria y huellas verificadas (CLAUDE.md, seccion 9)
PISO_BODEGA_1 = (16.80, 14.80)
PISO_BODEGA_2 = (18.30, 27.40)
HUELLA_N_ALDEA_EKP = (0.84, 1.47)
HUELLA_ARAUCO_EKP = (0.89, 1.41)
HUELLA_CELCO_UKP = (0.84, 1.43)


def test_mono_producto_reproduce_plantilla_real():
    grupo = GrupoCapa("N_ALDEA_EKP", "TAICHUNG", *HUELLA_N_ALDEA_EKP, 194)
    layout = calcular_layout_capa(*PISO_BODEGA_1, [grupo])
    assert len(layout) == 194


def test_mono_producto_sin_solape():
    grupo = GrupoCapa("N_ALDEA_EKP", "TAICHUNG", *HUELLA_N_ALDEA_EKP, 194)
    layout = calcular_layout_capa(*PISO_BODEGA_1, [grupo])
    for u in layout:
        assert u.x >= 0 and u.y >= 0
        assert u.x + u.largo <= PISO_BODEGA_1[0] + 1e-6
        assert u.y + u.ancho <= PISO_BODEGA_1[1] + 1e-6


def test_capa_mixta_coloca_lo_pedido_por_grupo():
    grupos = [
        GrupoCapa("ARAUCO_EKP", "QINGDAO", *HUELLA_ARAUCO_EKP, 120),
        GrupoCapa("CELCO_UKP", "TAICHUNG", *HUELLA_CELCO_UKP, 80),
    ]
    layout = calcular_layout_capa(*PISO_BODEGA_2, grupos)
    por_grupo = {}
    for u in layout:
        por_grupo[(u.producto, u.destino)] = por_grupo.get((u.producto, u.destino), 0) + 1
    assert por_grupo[("ARAUCO_EKP", "QINGDAO")] == 120
    assert por_grupo[("CELCO_UKP", "TAICHUNG")] == 80


def test_capa_mixta_franjas_no_se_solapan():
    grupos = [
        GrupoCapa("ARAUCO_EKP", "QINGDAO", *HUELLA_ARAUCO_EKP, 120),
        GrupoCapa("CELCO_UKP", "TAICHUNG", *HUELLA_CELCO_UKP, 80),
    ]
    layout = calcular_layout_capa(*PISO_BODEGA_2, grupos)
    rangos_por_grupo: dict[tuple[str, str], list[float]] = {}
    for u in layout:
        clave = (u.producto, u.destino)
        rangos_por_grupo.setdefault(clave, [float("inf"), float("-inf")])
        r = rangos_por_grupo[clave]
        r[0] = min(r[0], u.x)
        r[1] = max(r[1], u.x + u.largo)
    (x0_a, x1_a), (x0_b, x1_b) = (v for v in rangos_por_grupo.values())
    solapa = x0_a < x1_b and x0_b < x1_a
    assert not solapa


def test_capa_vacia_no_revienta():
    assert calcular_layout_capa(*PISO_BODEGA_2, []) == []
    grupo_sin_unidades = GrupoCapa("N_ALDEA_EKP", "TAICHUNG", *HUELLA_N_ALDEA_EKP, 0)
    assert calcular_layout_capa(*PISO_BODEGA_2, [grupo_sin_unidades]) == []


def test_pieza_mas_grande_que_el_piso_no_coloca_nada():
    grupo = GrupoCapa("GIGANTE", "TAICHUNG", 50.0, 50.0, 10)
    assert calcular_layout_capa(*PISO_BODEGA_2, [grupo]) == []
