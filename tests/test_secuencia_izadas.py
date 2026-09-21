"""
Tests de src/secuencia_izadas.py.

Cubre agrupamiento en bloques de 16 (marco de grua, CLAUDE.md seccion 9),
orden por rotacion de destino, y el caso de una capa vacia.
"""

from layout_capa import UnidadPosicion
from secuencia_izadas import UNIDADES_POR_IZADA, calcular_secuencia, ordenar_unidades

ROT = {"TAICHUNG": 1, "QINGDAO": 2, "KUNSAN": 3, "ULSAN": 4}


def _unidades(n, producto="N_ALDEA_EKP", destino="TAICHUNG", x=0.0):
    return [
        UnidadPosicion(x=x, y=i * 1.0, largo=0.84, ancho=1.0, rotado=False,
                        producto=producto, destino=destino)
        for i in range(n)
    ]


def test_agrupa_en_bloques_de_16():
    layout = _unidades(35)
    izadas = calcular_secuencia(layout, ROT)
    assert [iz.cantidad for iz in izadas] == [16, 16, 3]
    assert sum(iz.cantidad for iz in izadas) == 35


def test_numeracion_consecutiva():
    izadas = calcular_secuencia(_unidades(40), ROT)
    assert [iz.numero for iz in izadas] == [1, 2, 3]


def test_capa_vacia_no_produce_izadas():
    assert calcular_secuencia([], ROT) == []


def test_orden_prioriza_destino_de_descarga_tardia():
    unidades_taichung = _unidades(5, destino="TAICHUNG", x=0.0)
    unidades_ulsan = _unidades(5, destino="ULSAN", x=5.0)
    layout = unidades_taichung + unidades_ulsan
    ordenadas = ordenar_unidades(layout, ROT)
    assert ordenadas[0].destino == "ULSAN"
    assert ordenadas[-1].destino == "TAICHUNG"


def test_una_izada_no_supera_el_marco_de_la_grua():
    izadas = calcular_secuencia(_unidades(50), ROT)
    for iz in izadas:
        assert iz.cantidad <= UNIDADES_POR_IZADA
