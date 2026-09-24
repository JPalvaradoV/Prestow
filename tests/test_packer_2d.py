"""
Tests del packer (capacidad geométrica por bodega y producto).

La referencia es data/capacidades.csv, el artefacto versionado que consume
el modelo: regenerarlo desde datos_entrada_kiwi_arrow.xlsx tiene que dar
exactamente lo mismo (si no, el CSV quedó desactualizado respecto de los
datos — CLAUDE.md sección 8, "cambiar configuración sin regenerar
artefactos").
"""

import csv

import packer_2d


def test_regenerar_da_el_mismo_csv_versionado():
    bodegas, productos = packer_2d.leer_entrada("data/datos_entrada_kiwi_arrow.xlsx")
    filas = packer_2d.generar_tabla(bodegas, productos, mostrar=False)
    with open("data/capacidades.csv", newline="", encoding="utf-8-sig") as f:
        versionado = {(int(r["bodega"]), r["producto"]): int(r["unidades_max"]) for r in csv.DictReader(f)}
    generado = {(f["bodega"], f["producto"]): f["unidades_max"] for f in filas}
    assert len(generado) == 40
    assert generado == versionado


def test_capacidad_nunca_supera_el_area():
    # 8 bodegas x 5 productos del caso base: la huella total no puede exceder el piso
    bodegas, productos = packer_2d.leer_entrada("data/datos_entrada_kiwi_arrow.xlsx")
    for fila in packer_2d.generar_tabla(bodegas, productos, mostrar=False):
        assert fila["area_ocupada_m2"] <= fila["area_piso_m2"]


def test_mejor_patron_nunca_peor_que_uniforme():
    # Bodegas 2-8 del caso base (18,30 x 27,40 m) con la huella de ARAUCO_EKP
    neto, bruto, _ = packer_2d.calcular_capacidad(18.30, 27.40, 0.89, 1.41)
    uniforme, _ = packer_2d.patron_uniforme(18.30, 27.40, 0.89, 1.41)
    assert bruto >= uniforme
    assert neto == bruto  # MERMA = 0, supuesto avalado
