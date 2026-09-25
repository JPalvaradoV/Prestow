"""
Generador de instancias de prueba para los informes (Tecnico, seccion 8;
Academico, subtareas 11-12).

POR QUE EXISTE: sin contacto con la contraparte no hay mas prestows reales
que el del Kiwi Arrow, y ambos informes exigen probar el sistema con
instancias distintas, cada una con una pregunta declarada ("esta instancia
verifica el comportamiento con un solo destino, esta con seis").

METODO: perturbacion del caso real, el que usa la literatura de estiba de
contenedores cuando no hay mas casos reales. Se parte del caso base (buque,
productos, rotacion y viaje del Kiwi Arrow) y se cambia UNA cosa por
instancia: la carga, los destinos, los productos, las bodegas activas o el
tamano del buque. Asi cada resultado se puede atribuir a ese cambio.

No inventa datos fisicos nuevos: las bodegas agregadas en las instancias de
tamano son copias exactas de las bodegas 2-8 (18,30 x 27,40 m), los productos
son los cinco verificados, y los destinos agregados se llaman DESTINO_5 y
DESTINO_6 para que nadie los confunda con puertos reales.

Funciones puras: reciben y devuelven Instancia; escribir_csv() es la unica
que toca disco. El formato de salida es el mismo que lee
modelo_prestow.cargar_desde_csv (buque_*, productos_*, rotacion_*, viaje_*).
"""

from __future__ import annotations

import copy
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Instancia:
    id: str
    grupo: str       # "pruebas", "rendimientos" o "tamano"
    proposito: str   # la pregunta que responde la instancia
    buque: list[dict]
    productos: list[dict]
    rotacion: list[dict]
    viaje: list[dict]
    # Tiempo de ciclo por bodega en minutos, si difiere del caso base (solo
    # las instancias de rendimientos). None = el del modelo.
    tiempo_ciclo_min: dict[int, float] | None = None
    descripcion: str = ""
    notas: list[str] = field(default_factory=list)

    def tamano(self) -> dict:
        return {
            "bodegas": len(self.buque),
            "destinos": len(self.rotacion),
            "productos": len({f["producto"] for f in self.viaje}),
            "unidades": sum(f["unidades"] for f in self.viaje),
        }


# Tiempo de ciclo del caso base (minutos), derivado de las horas declaradas
# en el archivo del puerto. Igual a modelo_prestow.TIEMPO_CICLO_POR_BODEGA.
TIEMPO_CICLO_BASE_MIN = {8: 7.14, 7: 7.19, 6: 7.11, 5: 7.19, 4: 7.15, 3: 7.16, 2: 7.16, 1: 13.91}
RENDIMIENTO_BASE_T_H = {1: 140.0}  # bodegas 2-8: 270 t/h
RENDIMIENTO_RESTO_T_H = 270.0


# =============================================================================
# Lectura del caso base
# =============================================================================

def _filas(ws, columnas: list[str]) -> list[dict]:
    fila_enc = None
    for r in range(1, 12):
        if str(ws.cell(row=r, column=1).value or "").strip() == columnas[0]:
            fila_enc = r
            break
    if fila_enc is None:
        raise ValueError(f"En la hoja '{ws.title}' falta la columna '{columnas[0]}'")
    salida = []
    r = fila_enc + 1
    while True:
        primera = ws.cell(row=r, column=1).value
        if primera is None or str(primera).strip() in ("", "TOTAL"):
            break
        salida.append({c: ws.cell(row=r, column=j).value for j, c in enumerate(columnas, start=1)})
        r += 1
    return salida


def leer_caso_base(ruta_excel: str | Path) -> Instancia:
    """Lee el Excel de entrada del caso base (hojas Buque, Productos, Rotacion, Viaje)."""
    from openpyxl import load_workbook

    wb = load_workbook(ruta_excel, data_only=True)
    buque = [
        {"bodega": int(f["bodega"]), "largo_m": float(f["largo_m"]), "ancho_m": float(f["ancho_m"]),
         "planes": int(f["planes"]), "cuadrilla": int(f["cuadrilla"])}
        for f in _filas(wb["Buque"], ["bodega", "largo_m", "ancho_m", "planes", "cuadrilla"])
    ]
    productos = [
        {"producto": str(f["producto"]).strip(), "huella_largo_m": float(f["huella_largo_m"]),
         "huella_ancho_m": float(f["huella_ancho_m"]), "peso_t": float(f["peso_t"]),
         "origen_dato": str(f["origen_dato"] or "")}
        for f in _filas(wb["Productos"], ["producto", "huella_largo_m", "huella_ancho_m", "peso_t", "origen_dato"])
    ]
    rotacion = [
        {"destino": str(f["destino"]).strip().upper(), "orden_descarga": int(f["orden_descarga"])}
        for f in _filas(wb["Rotacion"], ["destino", "orden_descarga", "nota"])
    ]
    viaje = [
        {"producto": str(f["producto"]).strip(), "destino": str(f["destino"]).strip().upper(),
         "unidades": int(f["unidades"])}
        for f in _filas(wb["Viaje"], ["producto", "destino", "unidades"])
    ]
    return Instancia(
        id="P0", grupo="pruebas",
        proposito="¿El sistema reproduce el plan real y cómo se compara con él? (línea base)",
        buque=buque, productos=productos, rotacion=rotacion, viaje=viaje,
        descripcion="Caso base Kiwi Arrow sin cambios.",
    )


# =============================================================================
# Transformaciones (cada una cambia UNA cosa)
# =============================================================================

def _nueva(base: Instancia, id_: str, grupo: str, proposito: str, descripcion: str) -> Instancia:
    inst = copy.deepcopy(base)
    inst.id, inst.grupo, inst.proposito, inst.descripcion = id_, grupo, proposito, descripcion
    inst.tiempo_ciclo_min = copy.deepcopy(base.tiempo_ciclo_min)
    inst.notas = []
    return inst


def _agrupar(viaje: list[dict]) -> list[dict]:
    total: dict[tuple[str, str], int] = {}
    for f in viaje:
        if f["unidades"] > 0:
            clave = (f["producto"], f["destino"])
            total[clave] = total.get(clave, 0) + f["unidades"]
    return [{"producto": p, "destino": d, "unidades": u} for (p, d), u in sorted(total.items())]


def escalar_carga(inst: Instancia, factor: float) -> Instancia:
    """Multiplica las unidades de cada fila del viaje (redondeo, mínimo 1)."""
    inst.viaje = _agrupar(
        [{**f, "unidades": max(1, round(f["unidades"] * factor))} for f in inst.viaje]
    )
    return inst


def fusionar_destinos(inst: Instancia, mapa: dict[str, str]) -> Instancia:
    """Reemplaza destinos según `mapa` y renumera la rotación de 1 en adelante."""
    inst.viaje = _agrupar([{**f, "destino": mapa.get(f["destino"], f["destino"])} for f in inst.viaje])
    orden_viejo = {r["destino"]: r["orden_descarga"] for r in inst.rotacion}
    quedan = sorted({mapa.get(d, d) for d in orden_viejo}, key=lambda d: orden_viejo[d])
    inst.rotacion = [{"destino": d, "orden_descarga": i} for i, d in enumerate(quedan, start=1)]
    return inst


def dividir_destino(inst: Instancia, destino: str, nuevo: str, fraccion: float) -> Instancia:
    """
    Pasa `fraccion` de la carga de `destino` a un destino nuevo, que se
    descarga justo después de `destino`. Renumera la rotación.
    """
    viaje = []
    for f in inst.viaje:
        if f["destino"] == destino:
            parte = round(f["unidades"] * fraccion)
            viaje.append({**f, "unidades": f["unidades"] - parte})
            viaje.append({**f, "destino": nuevo, "unidades": parte})
        else:
            viaje.append(f)
    inst.viaje = _agrupar(viaje)
    orden = sorted(inst.rotacion, key=lambda r: r["orden_descarga"])
    nombres = []
    for r in orden:
        nombres.append(r["destino"])
        if r["destino"] == destino:
            nombres.append(nuevo)
    inst.rotacion = [{"destino": d, "orden_descarga": i} for i, d in enumerate(nombres, start=1)]
    return inst


def un_solo_producto(inst: Instancia, producto: str) -> Instancia:
    """Toda la carga pasa a ser `producto`, conservando las unidades por destino."""
    inst.viaje = _agrupar([{**f, "producto": producto} for f in inst.viaje])
    inst.productos = [p for p in inst.productos if p["producto"] == producto]
    return inst


def repartir_por_destino(inst: Instancia, fracciones: dict[str, float]) -> Instancia:
    """
    Redistribuye el total de unidades entre destinos según `fracciones`,
    conservando la mezcla de productos del caso base.
    """
    total = sum(f["unidades"] for f in inst.viaje)
    por_producto: dict[str, int] = {}
    for f in inst.viaje:
        por_producto[f["producto"]] = por_producto.get(f["producto"], 0) + f["unidades"]
    viaje = []
    for p, u_p in por_producto.items():
        for d, fr in fracciones.items():
            viaje.append({"producto": p, "destino": d, "unidades": round(u_p * fr)})
    inst.viaje = _agrupar(viaje)
    inst.notas.append(f"Total original {total}; tras redondeo {sum(f['unidades'] for f in inst.viaje)}")
    return inst


def desactivar_bodegas(inst: Instancia, bodegas: list[int]) -> Instancia:
    """Quita bodegas del buque (quedan vacías, como en viajes reales parciales)."""
    inst.buque = [b for b in inst.buque if b["bodega"] not in bodegas]
    return inst


def agregar_bodegas(inst: Instancia, cantidad: int) -> Instancia:
    """
    Agrega bodegas idénticas a las 2-8 (18,30 x 27,40 m), numeradas a
    continuación, de a pares en cuadrillas nuevas. Tiempo de ciclo: el
    promedio de las bodegas normales (modelo_prestow.TIEMPO_CICLO).
    """
    modelo = next(b for b in inst.buque if b["bodega"] == 2)
    ultimo = max(b["bodega"] for b in inst.buque)
    cuadrilla = max(b["cuadrilla"] for b in inst.buque)
    for i in range(cantidad):
        if i % 2 == 0:
            cuadrilla += 1
        inst.buque.append({**modelo, "bodega": ultimo + i + 1, "cuadrilla": cuadrilla})
    return inst


def con_rendimientos(inst: Instancia, rendimiento_t_h: dict[int, float]) -> Instancia:
    """
    Cambia el rendimiento (t/h) de las bodegas indicadas. El tiempo de ciclo
    es inversamente proporcional al rendimiento: tc = tc_base x r_base / r.
    Es la misma relación que dio los 13,91 min de la bodega 1 (140 t/h) y
    los ~7,15 min del resto (270 t/h).
    """
    tc = dict(inst.tiempo_ciclo_min or TIEMPO_CICLO_BASE_MIN)
    for h, r in rendimiento_t_h.items():
        r_base = RENDIMIENTO_BASE_T_H.get(h, RENDIMIENTO_RESTO_T_H)
        tc[h] = TIEMPO_CICLO_BASE_MIN[h] * r_base / r
    inst.tiempo_ciclo_min = tc
    return inst


# =============================================================================
# Los tres conjuntos de instancias
# =============================================================================

def instancias_de_prueba(base: Instancia) -> list[Instancia]:
    """Técnico 8.21 / Académico 4.11: una pregunta por instancia."""
    out = [copy.deepcopy(base)]

    i = _nueva(base, "P1", "pruebas",
               "¿Qué pasa con un solo destino, donde no hay riesgo de overstowage?",
               "Toda la carga va a QINGDAO.")
    out.append(fusionar_destinos(i, {d["destino"]: "QINGDAO" for d in base.rotacion}))

    i = _nueva(base, "P2", "pruebas",
               "¿Qué pasa con un solo producto, el de mayor huella (buque casi lleno)?",
               "Toda la carga pasa a ARAUCO_EKP (0,89 x 1,41 m), mismas unidades por destino.")
    out.append(un_solo_producto(i, "ARAUCO_EKP"))

    i = _nueva(base, "P3", "pruebas",
               "¿Funciona con bodegas vacías, como en viajes reales parciales?",
               "Bodegas 3 y 6 inactivas (así aparecen en hojas históricas del archivo del "
               "puerto); carga al 75%.")
    out.append(escalar_carga(desactivar_bodegas(i, [3, 6]), 0.75))

    i = _nueva(base, "P4", "pruebas",
               "¿Cómo reparte con el buque a media carga?",
               "Carga al 50%.")
    out.append(escalar_carga(i, 0.50))

    i = _nueva(base, "P5", "pruebas",
               "¿Qué pasa si casi toda la carga es del último destino (fondo pesado)?",
               "70% de las unidades a ULSAN (último), 10% a cada uno de los otros tres; "
               "misma mezcla de productos.")
    out.append(repartir_por_destino(i, {"TAICHUNG": 0.10, "QINGDAO": 0.10, "KUNSAN": 0.10, "ULSAN": 0.70}))

    i = _nueva(base, "P6", "pruebas",
               "¿Qué pasa con seis destinos (más restricciones de apilamiento)?",
               "Mitad de QINGDAO pasa a DESTINO_5 (después de QINGDAO) y mitad de KUNSAN a "
               "DESTINO_6 (después de KUNSAN).")
    out.append(dividir_destino(dividir_destino(i, "QINGDAO", "DESTINO_5", 0.5), "KUNSAN", "DESTINO_6", 0.5))

    i = _nueva(base, "P7", "pruebas",
               "¿El sistema rechaza con un mensaje claro una carga que no cabe?",
               "Carga al 130%: excede el área del buque.")
    out.append(escalar_carga(i, 1.30))
    return out


def instancias_rendimientos(base: Instancia) -> list[Instancia]:
    """
    Académico 8.26 (análisis obligatorio según la guía de tareas): el
    rendimiento t/h es el supuesto no verificado que crea el cuello de
    botella de la bodega 1.
    """
    out = []
    for r in (180, 220, 270):
        i = _nueva(base, f"R_b1_{r}", "rendimientos",
                   f"¿Cuánto cambia el resultado si la bodega 1 rinde {r} t/h en vez de 140?",
                   f"Bodega 1 a {r} t/h (tiempo de ciclo {TIEMPO_CICLO_BASE_MIN[1] * 140 / r:.2f} min).")
        out.append(con_rendimientos(i, {1: r}))
    for signo, factor in (("menos10", 0.90), ("mas10", 1.10)):
        i = _nueva(base, f"R_todas_{signo}", "rendimientos",
                   f"¿Cuánto cambia si todas las bodegas rinden {factor:.0%} de lo supuesto?",
                   f"Todos los rendimientos x {factor}.")
        out.append(con_rendimientos(
            i, {h: RENDIMIENTO_BASE_T_H.get(h, RENDIMIENTO_RESTO_T_H) * factor for h in TIEMPO_CICLO_BASE_MIN}
        ))
    return out


def instancias_tamano(base: Instancia) -> list[Instancia]:
    """
    Técnico 7.16/7.19 y Académico 8.26: cómo crecen el tiempo y el gap con
    el tamaño (bodegas y destinos a la vez, carga proporcional a las bodegas).
    El caso base (8 bodegas, 4 destinos) es P0.
    """
    out = []
    i = _nueva(base, "T4x2", "tamano", "Tamaño chico: 4 bodegas, 2 destinos",
               "Bodegas 8-5 (2 cuadrillas); TAICHUNG+QINGDAO -> QINGDAO, KUNSAN+ULSAN -> ULSAN; carga al 50%.")
    i = desactivar_bodegas(i, [4, 3, 2, 1])
    out.append(escalar_carga(fusionar_destinos(i, {"TAICHUNG": "QINGDAO", "KUNSAN": "ULSAN"}), 0.50))

    i = _nueva(base, "T6x3", "tamano", "Tamaño medio: 6 bodegas, 3 destinos",
               "Bodegas 8-3 (3 cuadrillas); KUNSAN -> ULSAN; carga al 75%.")
    i = desactivar_bodegas(i, [2, 1])
    out.append(escalar_carga(fusionar_destinos(i, {"KUNSAN": "ULSAN"}), 0.75))

    i = _nueva(base, "T10x5", "tamano", "Tamaño grande: 10 bodegas, 5 destinos",
               "Caso base + bodegas 9-10 (cuadrilla 5) + DESTINO_5 (mitad de QINGDAO); carga al 125%.")
    i = agregar_bodegas(i, 2)
    out.append(escalar_carga(dividir_destino(i, "QINGDAO", "DESTINO_5", 0.5), 1.25))

    i = _nueva(base, "T12x6", "tamano", "Tamaño muy grande: 12 bodegas, 6 destinos",
               "Caso base + bodegas 9-12 (cuadrillas 5-6) + DESTINO_5 y DESTINO_6; carga al 150%.")
    i = agregar_bodegas(i, 4)
    i = dividir_destino(dividir_destino(i, "QINGDAO", "DESTINO_5", 0.5), "KUNSAN", "DESTINO_6", 0.5)
    out.append(escalar_carga(i, 1.50))
    return out


# =============================================================================
# Escritura
# =============================================================================

def escribir_csv(inst: Instancia, carpeta: str | Path) -> Path:
    """
    Escribe la instancia en el formato de modelo_prestow.cargar_desde_csv, más
    un instancia.json con id, pregunta, descripción, tamaño y tiempos de ciclo.
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    tablas = {
        "buque": (inst.buque, ["bodega", "largo_m", "ancho_m", "planes", "cuadrilla"]),
        "productos": (inst.productos, ["producto", "huella_largo_m", "huella_ancho_m", "peso_t", "origen_dato"]),
        "rotacion": (inst.rotacion, ["destino", "orden_descarga"]),
        "viaje": (inst.viaje, ["producto", "destino", "unidades"]),
    }
    for nombre, (filas, columnas) in tablas.items():
        with open(carpeta / f"{nombre}_{inst.id}.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
            wr.writeheader()
            wr.writerows(filas)
    meta = {
        "id": inst.id, "grupo": inst.grupo, "proposito": inst.proposito,
        "descripcion": inst.descripcion, "tamano": inst.tamano(),
        "tiempo_ciclo_min": inst.tiempo_ciclo_min, "notas": inst.notas,
    }
    (carpeta / "instancia.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return carpeta


def todas(ruta_caso_base: str | Path) -> list[Instancia]:
    base = leer_caso_base(ruta_caso_base)
    return instancias_de_prueba(base) + instancias_rendimientos(base) + instancias_tamano(base)
