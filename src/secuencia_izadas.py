"""
Secuencia de izadas dentro de una capa - agrupa unidades en izadas de 16 y
decide el orden de carga.

POR QUE ES UN MODULO SEPARADO
El modelo de asignacion decide CUANTAS izadas necesita cada capa (variable z
en modelo_prestow.py) pero no en que orden se cargan las unidades dentro de
la capa: eso no afecta ninguna restriccion del modelo (supuesto 7, "sin
bloqueo entre destinos dentro de una capa"). Este modulo solo sirve para
mostrar en la web una secuencia de carga plausible, consumiendo el layout de
layout_capa.py.

CRITERIO DE ORDEN (heuristico, no viene del modelo):
1. Destino, en el orden de la rotacion de descarga (ROT): se carga primero el
   destino que se descarga al final, para no tener que reordenar dentro de la
   capa. Como no hay bloqueo declarado dentro de una capa esto es una
   convencion de visualizacion, no una restriccion verificada.
2. Producto, alfabetico, para que la grua no alterne de fardo todo el tiempo.
3. Posicion: barrido en serpentina (boustrophedon) columna por columna,
   alternando la direccion en y para minimizar el desplazamiento de la grua
   entre unidades consecutivas.
"""

from __future__ import annotations

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


def _clave_orden(u: UnidadPosicion, rot: dict[str, int], columnas: list[float]):
    col_idx = columnas.index(u.x)
    y_orden = u.y if col_idx % 2 == 0 else -u.y
    return (-rot.get(u.destino, 0), u.producto, col_idx, y_orden)


def ordenar_unidades(layout: list[UnidadPosicion], rot: dict[str, int]) -> list[UnidadPosicion]:
    """Ordena las unidades de una capa segun el criterio de carga descrito arriba."""
    if not layout:
        return []
    columnas = sorted({u.x for u in layout})
    return sorted(layout, key=lambda u: _clave_orden(u, rot, columnas))


def calcular_secuencia(layout: list[UnidadPosicion], rot: dict[str, int],
                        unidades_por_izada: int = UNIDADES_POR_IZADA) -> list[Izada]:
    """
    Agrupa las unidades ya ordenadas en izadas de tamano unidades_por_izada
    (la ultima puede quedar incompleta).
    """
    ordenadas = ordenar_unidades(layout, rot)
    izadas = []
    for i in range(0, len(ordenadas), unidades_por_izada):
        grupo = ordenadas[i:i + unidades_por_izada]
        izadas.append(Izada(numero=len(izadas) + 1, unidades=grupo))
    return izadas
