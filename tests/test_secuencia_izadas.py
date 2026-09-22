"""
Tests de src/secuencia_izadas.py.

Cubre el agrupamiento en bloques RECTANGULARES compactos de hasta 16
unidades (marco de grua, CLAUDE.md seccion 9) -- no basta con que la
cantidad sea correcta, cada bloque tiene que ser un rectangulo real de la
grilla (fila, columna), sin huecos ni forma de L -- ademas del orden por
rotacion de destino y el caso de una capa vacia.
"""

from layout_capa import UnidadPosicion
from secuencia_izadas import UNIDADES_POR_IZADA, calcular_secuencia, ordenar_unidades

ROT = {"TAICHUNG": 1, "QINGDAO": 2, "KUNSAN": 3, "ULSAN": 4}


def _unidades_columna(n, producto="N_ALDEA_EKP", destino="TAICHUNG"):
    """n unidades en una sola columna de la grilla (fila 0..n-1, columna 0)."""
    return [
        UnidadPosicion(x=0.0, y=i * 1.0, largo=0.84, ancho=1.0, rotado=False,
                        producto=producto, destino=destino, fila=i, columna=0)
        for i in range(n)
    ]


def _unidades_grilla(filas, columnas, producto="N_ALDEA_EKP", destino="TAICHUNG"):
    """Una grilla completa de filas x columnas unidades."""
    return [
        UnidadPosicion(x=c * 0.84, y=f * 1.0, largo=0.84, ancho=1.0, rotado=False,
                        producto=producto, destino=destino, fila=f, columna=c)
        for f in range(filas)
        for c in range(columnas)
    ]


def _es_rectangulo(bloque: list[UnidadPosicion]) -> bool:
    """True si las (fila, columna) del bloque forman un rectangulo compacto
    (todas las combinaciones del rango fila x columna estan presentes, sin
    huecos y sin nada fuera de ese rango)."""
    filas = {u.fila for u in bloque}
    columnas = {u.columna for u in bloque}
    esperado = len(filas) * len(columnas)
    return len(bloque) == esperado


def test_agrupa_en_bloques_de_16():
    layout = _unidades_columna(35)
    izadas = calcular_secuencia(layout, ROT)
    assert [iz.cantidad for iz in izadas] == [16, 16, 3]
    assert sum(iz.cantidad for iz in izadas) == 35


def test_numeracion_consecutiva():
    izadas = calcular_secuencia(_unidades_columna(40), ROT)
    assert [iz.numero for iz in izadas] == [1, 2, 3]


def test_capa_vacia_no_produce_izadas():
    assert calcular_secuencia([], ROT) == []


def test_orden_prioriza_destino_de_descarga_tardia():
    unidades_taichung = _unidades_columna(5, destino="TAICHUNG")
    unidades_ulsan = _unidades_columna(5, destino="ULSAN")
    layout = unidades_taichung + unidades_ulsan
    ordenadas = ordenar_unidades(layout, ROT)
    assert ordenadas[0].destino == "ULSAN"
    assert ordenadas[-1].destino == "TAICHUNG"


def test_una_izada_no_supera_el_marco_de_la_grua():
    izadas = calcular_secuencia(_unidades_columna(50), ROT)
    for iz in izadas:
        assert iz.cantidad <= UNIDADES_POR_IZADA


def test_bloques_son_rectangulos_compactos_no_forma_de_l():
    """El caso que motivo el rediseño: una grilla donde el ancho no es
    múltiplo del alto del bloque debía dejar antes una izada en forma de L
    (parte de una columna + parte de la siguiente). Ahora cada izada debe
    ser un rectángulo real de la grilla."""
    layout = _unidades_grilla(filas=10, columnas=20)  # 200 unidades, igual que bodega 1
    izadas = calcular_secuencia(layout, ROT)
    assert sum(iz.cantidad for iz in izadas) == 200
    for iz in izadas:
        assert _es_rectangulo(iz.unidades), f"izada {iz.numero} no es un rectángulo compacto"


def test_bloque_10x20_es_cuadrado_de_4x4():
    """Para una grilla 10x20 y capacidad 16, el bloque más parecido a un
    cuadrado que cabe es 4x4=16 (no 1x16, aunque ambos usan 16 unidades)."""
    layout = _unidades_grilla(filas=10, columnas=20)
    izadas = calcular_secuencia(layout, ROT)
    primera = izadas[0]
    assert primera.cantidad == 16
    filas = {u.fila for u in primera.unidades}
    columnas = {u.columna for u in primera.unidades}
    assert len(filas) == 4
    assert len(columnas) == 4


def test_bloques_no_se_superponen_y_cubren_toda_la_grilla():
    layout = _unidades_grilla(filas=7, columnas=13)  # dimensiones no multiplos de 16
    izadas = calcular_secuencia(layout, ROT)
    vistos = set()
    for iz in izadas:
        for u in iz.unidades:
            clave = (u.fila, u.columna)
            assert clave not in vistos, "una unidad no puede estar en dos izadas"
            vistos.add(clave)
    assert len(vistos) == 7 * 13


def test_capa_mixta_no_mezcla_grupos_en_una_izada():
    layout = _unidades_grilla(5, 5, producto="ARAUCO_EKP", destino="QINGDAO") + \
        _unidades_grilla(5, 5, producto="CELCO_UKP", destino="TAICHUNG")
    izadas = calcular_secuencia(layout, ROT)
    for iz in izadas:
        assert len(iz.productos) == 1
        assert len(iz.destinos) == 1
