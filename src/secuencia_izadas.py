"""
Secuencia de izadas dentro de una capa - agrupa unidades en izadas de 16
como bloques rectangulares compactos, y decide el orden de carga.

POR QUE ES UN MODULO SEPARADO
El modelo de asignacion decide CUANTAS izadas necesita cada capa (variable z
en modelo_prestow.py) pero no en que orden se cargan las unidades dentro de
la capa: eso no afecta ninguna restriccion del modelo (supuesto 7, "sin
bloqueo entre destinos dentro de una capa"). Este modulo solo sirve para
mostrar en la web y en el Excel una secuencia de carga fisicamente plausible,
consumiendo el layout de layout_capa.py.

POR QUE BLOQUES RECTANGULARES, NO CONTEO LINEAL
La primera version agrupaba simplemente contando 16 unidades en el orden de
barrido (columna por columna). Eso arma izadas correctas en CANTIDAD pero no
en FORMA: si una columna tiene menos de 16 unidades, la izada se completaba
con el resto de la columna siguiente, dejando un grupo en forma de L -- una
grua real no levanta 16 fardos desparramados en dos columnas distintas como
si fueran uno solo, los levanta juntos porque estan amarrados en un bloque
compacto. Se detecto probando la hoja "Planimetria" del Excel: se veian
grupos claramente no rectangulares.

Ahora cada izada es un BLOQUE RECTANGULAR de la grilla (fila, columna) que
arma layout_capa.py: se elige el rectangulo mas parecido a un cuadrado que
quepa en <=16 unidades (ver _dimensiones_bloque), y se tila toda la grilla
de cada grupo (producto, destino) con ese tamano de bloque. Los bloques del
borde pueden quedar con menos de 16 si la grilla no es multiplo exacto --
igual que antes, eso se interpreta como una izada parcial.

CRITERIO DE ORDEN (heuristico, no viene del modelo):
1. Destino, en el orden de la rotacion de descarga (ROT): se carga primero el
   destino que se descarga al final, para no tener que reordenar dentro de la
   capa. Como no hay bloqueo declarado dentro de una capa esto es una
   convencion de visualizacion, no una restriccion verificada.
2. Producto, alfabetico, para que la grua no alterne de fardo todo el tiempo.
3. Posicion: los bloques se recorren en barrido de fila (de arriba hacia
   abajo), alternando la direccion de columna en cada fila de bloques
   (serpentina), para minimizar el desplazamiento de la grua entre un
   bloque y el siguiente.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

try:
    from .layout_capa import UnidadPosicion
except ImportError:
    from layout_capa import UnidadPosicion  # type: ignore[import]

UNIDADES_POR_IZADA = 16


@dataclass
class Izada:
    """Un grupo de hasta UNIDADES_POR_IZADA unidades que mueve la grua de una vez."""

    numero: int
    unidades: list[UnidadPosicion]

    @property
    def cantidad(self) -> int:
        return len(self.unidades)

    @property
    def productos(self) -> set[str]:
        return {u.producto for u in self.unidades}

    @property
    def destinos(self) -> set[str]:
        return {u.destino for u in self.unidades}


def _dimensiones_bloque(filas: int, columnas: int, capacidad: int) -> tuple[int, int]:
    """
    Elige (alto, ancho) del bloque rectangular mas parecido a un cuadrado
    que quepa dentro de la grilla (filas x columnas) sin superar `capacidad`
    unidades. Maximiza el area (ideal: exactamente `capacidad`) y, entre
    los que logran el area maxima, prefiere la forma mas cuadrada.
    """
    mejor = (1, 1)
    mejor_area = 0
    for alto in range(1, min(filas, capacidad) + 1):
        ancho = min(columnas, capacidad // alto)
        if ancho <= 0:
            continue
        area = alto * ancho
        mas_cuadrado = abs(alto - ancho) < abs(mejor[0] - mejor[1])
        if area > mejor_area or (area == mejor_area and mas_cuadrado):
            mejor, mejor_area = (alto, ancho), area
    return mejor


def _bloques_del_grupo(unidades: list[UnidadPosicion],
                        unidades_por_izada: int) -> list[list[UnidadPosicion]]:
    """
    Tila la grilla (fila, columna) de un grupo (producto, destino) en
    bloques rectangulares compactos de hasta `unidades_por_izada` unidades
    cada uno. Recorre los bloques en serpentina para que la grua no salte de
    un extremo al otro entre un bloque y el siguiente.
    """
    if not unidades:
        return []

    indice = {(u.fila, u.columna): u for u in unidades}
    n_filas = max(u.fila for u in unidades) + 1
    n_columnas = max(u.columna for u in unidades) + 1
    alto, ancho = _dimensiones_bloque(n_filas, n_columnas, unidades_por_izada)

    bloques = []
    filas_bloque = list(range(0, n_filas, alto))
    for k, f0 in enumerate(filas_bloque):
        rango_columnas = range(0, n_columnas, ancho)
        if k % 2 == 1:
            rango_columnas = reversed(list(rango_columnas))
        for c0 in rango_columnas:
            bloque = [
                indice[(f, c)]
                for f in range(f0, min(f0 + alto, n_filas))
                for c in range(c0, min(c0 + ancho, n_columnas))
                if (f, c) in indice
            ]
            if bloque:
                bloques.append(bloque)
    return bloques


def ordenar_unidades(layout: list[UnidadPosicion], rot: dict[str, int]) -> list[UnidadPosicion]:
    """
    Devuelve las unidades agrupadas en bloques rectangulares y concatenadas
    en el orden de carga (ver criterio de orden en el docstring del módulo).
    No es un orden por unidad individual: preserva el agrupamiento en
    bloques para que calcular_secuencia no tenga que rehacer el trabajo.
    """
    if not layout:
        return []

    grupos: dict[tuple[str, str], list[UnidadPosicion]] = defaultdict(list)
    for u in layout:
        grupos[(u.producto, u.destino)].append(u)

    grupos_ordenados = sorted(
        grupos.items(),
        key=lambda kv: (-rot.get(kv[0][1], 0), kv[0][0]),
    )

    ordenadas: list[UnidadPosicion] = []
    for _clave, unidades in grupos_ordenados:
        for bloque in _bloques_del_grupo(unidades, UNIDADES_POR_IZADA):
            ordenadas.extend(bloque)
    return ordenadas


def calcular_secuencia(layout: list[UnidadPosicion], rot: dict[str, int],
                        unidades_por_izada: int = UNIDADES_POR_IZADA) -> list[Izada]:
    """
    Agrupa las unidades de la capa en izadas: cada una es un bloque
    rectangular compacto de hasta `unidades_por_izada` unidades (ver
    _dimensiones_bloque y _bloques_del_grupo), recorridos en el orden de
    carga del módulo.
    """
    if not layout:
        return []

    grupos: dict[tuple[str, str], list[UnidadPosicion]] = defaultdict(list)
    for u in layout:
        grupos[(u.producto, u.destino)].append(u)

    grupos_ordenados = sorted(
        grupos.items(),
        key=lambda kv: (-rot.get(kv[0][1], 0), kv[0][0]),
    )

    izadas: list[Izada] = []
    for _clave, unidades in grupos_ordenados:
        for bloque in _bloques_del_grupo(unidades, unidades_por_izada):
            izadas.append(Izada(numero=len(izadas) + 1, unidades=bloque))
    return izadas
