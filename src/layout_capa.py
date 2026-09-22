"""
Layout 2D de una capa - posiciones (x, y, rotacion) por grupo de unidades.

POR QUE ES UN MODULO SEPARADO
packer_2d.py calcula CUANTAS unidades caben (capacidad agregada). Este modulo
calcula DONDE queda cada grupo de unidades dentro del piso de la bodega, para
poder dibujar una planimetria visual tipo prestow. No participa del modelo de
asignacion: el modelo solo necesita capacidades.csv. layout_capa.py se llama
solo cuando la web tiene que mostrar el detalle visual de una capa ya resuelta.

SUPUESTO DECLARADO: cuando una capa mezcla mas de un producto o destino (85
capas del caso base, 5 mixtas), no existe un patron de empaquetamiento optimo
documentado para la mezcla. Se reparte el piso en franjas verticales
proporcionales al area que ocupa cada grupo y se rellena cada franja con el
mismo criterio de patron_uniforme de packer_2d.py. Es una aproximacion para
visualizacion, no una cota de capacidad: la capacidad real ya la valida
capacidades.csv / el modelo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UnidadPosicion:
    """Un rectangulo dentro del piso de la bodega: una unidad de carga."""

    x: float
    y: float
    largo: float
    ancho: float
    rotado: bool
    producto: str
    destino: str
    fila: int = 0
    """Indice de fila dentro de la grilla de SU PROPIO grupo (producto+destino),
    empezando en 0. Util para reconstruir la posicion exacta sin depender de
    coordenadas continuas (por ejemplo al dibujar una grilla en Excel)."""
    columna: int = 0
    """Indice de columna dentro de la grilla de su propio grupo, empezando en 0."""


@dataclass
class GrupoCapa:
    """Una combinacion (producto, destino) presente en una capa, con su huella."""

    producto: str
    destino: str
    largo_unidad: float
    ancho_unidad: float
    unidades: int


def obtener_huellas(ruta_datos: str | Path) -> dict[str, tuple[float, float]]:
    """
    Lee (largo, ancho) de cada producto desde el Excel/carpeta de entrada.

    HUELLA en modelo_prestow.py solo guarda el area (m2); aqui se necesitan
    las dos dimensiones por separado para poder dibujar el rectangulo.
    """
    try:
        from . import packer_2d
    except ImportError:
        import packer_2d  # type: ignore[import]

    _, productos = packer_2d.leer_entrada(ruta_datos)
    return {p: (l, w) for p, l, w, _ in productos}


def obtener_geometria_bodegas(ruta_datos: str | Path) -> dict[int, tuple[float, float]]:
    """Lee (largo, ancho) del piso de cada bodega desde el Excel/carpeta de entrada."""
    try:
        from . import packer_2d
    except ImportError:
        import packer_2d  # type: ignore[import]

    bodegas, _ = packer_2d.leer_entrada(ruta_datos)
    return {h: (l, w) for h, l, w in bodegas}


def _mejor_orientacion(largo_zona: float, ancho_zona: float,
                        largo_pieza: float, ancho_pieza: float) -> tuple[float, float, bool]:
    """
    Elige la orientacion (sin rotar o rotada 90) que cabe mas veces en la
    zona, igual que patron_uniforme de packer_2d.py.

    Devuelve (largo_efectivo, ancho_efectivo, rotado).
    """
    sin_rotar = math.floor(largo_zona / largo_pieza) * math.floor(ancho_zona / ancho_pieza)
    rotado = math.floor(largo_zona / ancho_pieza) * math.floor(ancho_zona / largo_pieza)
    if rotado > sin_rotar:
        return ancho_pieza, largo_pieza, True
    return largo_pieza, ancho_pieza, False


def _rellenar_zona(x0: float, y0: float, largo_zona: float, ancho_zona: float,
                    largo_pieza: float, ancho_pieza: float, n_unidades: int,
                    producto: str, destino: str) -> list[UnidadPosicion]:
    """Llena una zona rectangular con hasta n_unidades piezas en grilla uniforme."""
    if n_unidades <= 0 or largo_zona <= 0 or ancho_zona <= 0:
        return []

    le, an, rotado = _mejor_orientacion(largo_zona, ancho_zona, largo_pieza, ancho_pieza)
    cols = math.floor(largo_zona / le)
    filas = math.floor(ancho_zona / an)
    if cols <= 0 or filas <= 0:
        return []

    posiciones = []
    contador = 0
    for j in range(filas):
        for i in range(cols):
            if contador >= n_unidades:
                return posiciones
            posiciones.append(UnidadPosicion(
                x=x0 + i * le, y=y0 + j * an,
                largo=le, ancho=an, rotado=rotado,
                producto=producto, destino=destino,
                fila=j, columna=i,
            ))
            contador += 1
    return posiciones


def calcular_layout_capa(largo_piso: float, ancho_piso: float,
                          grupos: list[GrupoCapa]) -> list[UnidadPosicion]:
    """
    Calcula la posicion (x, y) de cada unidad de cada grupo dentro del piso.

    Con un solo grupo usa grilla uniforme sobre todo el piso (igual que el
    mejor patron de packer_2d.py para capas de un solo producto/destino, que
    son 80 de las 85 capas cargadas del caso base).

    Con varios grupos (capa mixta) reparte el piso en franjas verticales
    proporcionales al area que ocupa cada grupo, de mayor a menor, y llena
    cada franja en grilla uniforme. Ver nota de SUPUESTO en el docstring del
    modulo.
    """
    grupos = [g for g in grupos if g.unidades > 0]
    if not grupos:
        return []

    if len(grupos) == 1:
        g = grupos[0]
        return _rellenar_zona(0.0, 0.0, largo_piso, ancho_piso,
                               g.largo_unidad, g.ancho_unidad, g.unidades,
                               g.producto, g.destino)

    areas = [g.unidades * g.largo_unidad * g.ancho_unidad for g in grupos]
    area_total = sum(areas)
    if area_total <= 0:
        return []

    orden = sorted(range(len(grupos)), key=lambda i: areas[i], reverse=True)

    posiciones: list[UnidadPosicion] = []
    x_actual = 0.0
    largo_restante = largo_piso
    for k, idx in enumerate(orden):
        g = grupos[idx]
        if k == len(orden) - 1:
            ancho_franja = largo_restante
        else:
            ancho_franja = largo_piso * (areas[idx] / area_total)
            ancho_franja = min(ancho_franja, largo_restante)
        posiciones += _rellenar_zona(x_actual, 0.0, ancho_franja, ancho_piso,
                                      g.largo_unidad, g.ancho_unidad, g.unidades,
                                      g.producto, g.destino)
        x_actual += ancho_franja
        largo_restante -= ancho_franja

    return posiciones


def layout_para_fila_plan(bodega: int, plan: int, filas_plan: list,
                           piso: dict[int, tuple[float, float]],
                           huellas: dict[str, tuple[float, float]]) -> list[UnidadPosicion]:
    """
    Conveniencia: arma los GrupoCapa de una capa (bodega, plan) a partir de
    las filas del plan (objetos con .bodega, .plan, .producto, .destino,
    .unidades, como FilaPlan de api.py) y calcula su layout.
    """
    largo_piso, ancho_piso = piso[bodega]
    grupos = [
        GrupoCapa(
            producto=f.producto, destino=f.destino,
            largo_unidad=huellas[f.producto][0], ancho_unidad=huellas[f.producto][1],
            unidades=f.unidades,
        )
        for f in filas_plan
        if f.bodega == bodega and f.plan == plan
    ]
    return calcular_layout_capa(largo_piso, ancho_piso, grupos)
