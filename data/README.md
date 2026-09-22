# Datos del proyecto

## Versionados
- `datos_entrada_kiwi_arrow.xlsx` — caso base editable, cinco hojas
- `capacidades.csv` — salida del packer (40 combinaciones bodega × producto)
- `capacidades_reales_por_plan.csv` — capacidades reales por (bodega, plan,
  producto), extraídas de `raw/PLANIMETRIAS_MN_KIWI_ARROW_2025.xls` con
  `src/extraer_capacidades_reales.py`. Pisa el cálculo geométrico del packer
  donde hay dato verificado del puerto (ver `CAPACIDAD_POR_PLAN` en
  `modelo_prestow.py`). 72 combinaciones limpias — el script documenta en su
  docstring qué se descartó y por qué (productos ambiguos, conflictos entre
  plantillas, un valor extremo sin confirmar).
- `plan_estiba.xlsx` — salida de ejemplo del modelo (corrida de referencia)
- `stability_report.csv` — resultado de `stability_test.py` (5 semillas)

## `raw/`
Excels originales del puerto (`PRESTOW_N_10*.xls`, `PLANIMETRIAS_*.xls`). No se versionan.
Cada integrante tiene su copia local — para regenerar `capacidades_reales_por_plan.csv`,
poner `PLANIMETRIAS_MN_KIWI_ARROW_2025.xls` acá y correr
`python3 src/extraer_capacidades_reales.py`.
