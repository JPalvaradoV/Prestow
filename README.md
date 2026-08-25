# Prestow Lirquén — Optimización del plan de estiba

Herramienta de optimización del prestow de celulosa unitizada en buques open hatch, caso base **Kiwi Arrow** en Puerto Lirquén.

**Contexto:** Capstone Analytics 2026-02, Ingeniería UDD. 5 personas, 7 semanas + 1 de colchón.

## Estado

El modelo MILP está implementado, corrido y validado. Mejora el makespan del plan manual en 4% (58,19 h vs 60,61 h) y reproduce las horas del archivo del puerto con error de 0,01 h.

La **página web (Streamlit)** que envuelve el modelo está en construcción.

## Estructura

```
prestow-lirquen/
├── CLAUDE.md              # Contexto operacional para Claude Code (auto-cargado)
├── README.md              # Este archivo
├── requirements.txt
├── pyproject.toml
├── .gitignore
│
├── src/                   # Núcleo de optimización (ya implementado)
│   ├── modelo_prestow.py  # Modelo MILP completo
│   ├── packer_2d.py       # Cálculo de capacidad geométrica
│   ├── api.py             # (a construir) función pura resolver_prestow()
│   ├── layout_capa.py     # (a construir) posiciones dentro de la capa
│   ├── secuencia_izadas.py# (a construir) orden de carga por capa
│   ├── balance_peso.py    # (a construir) peso y densidad por bodega
│   └── stability_test.py  # (a construir) 5 semillas para estabilidad
│
├── app/                   # Página web Streamlit (en construcción)
│   ├── app.py             # Entry point
│   ├── pages/             # Pestañas de la app
│   └── components/        # Componentes reutilizables
│
├── data/
│   ├── datos_entrada_kiwi_arrow.xlsx  # Caso base editable
│   ├── capacidades.csv                # Salida del packer
│   ├── plan_estiba.xlsx               # Salida de ejemplo del modelo
│   └── raw/                           # Excels originales (git-ignored)
│
├── docs/                  # Documentación del proyecto
│   ├── 00_LEEME_PRIMERO_contexto.md
│   ├── Resumen_Trabajo_Realizado.md
│   ├── 03_Instrucciones_afinar_modelo.md
│   ├── 04_Prompt_Informe_Tecnico.md
│   ├── 01_Contexto_Informe_Academico.md
│   ├── Restricciones_Modelo_Prestow_Lirquen.pdf
│   ├── Guia_Informe_Tecnico_Prestow_Lirquen.pdf
│   ├── Guia_de_tareas_Prestow_Lirquen.pdf
│   └── Ejemplos_Trabajados_Prestow_Lirquen.pdf
│
├── planificacion/
│   ├── Carta_Gantt_Prestow_Lirquen_v7.xlsx
│   └── Bitacora_Semanal_Prestow_Lirquen.xlsx
│
├── tests/                 # pytest — validaciones sobre el caso base
└── notebooks/             # Exploración y verificación manual
```

## Puesta en marcha

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Correr el modelo por CLI (funciona hoy)
python3 src/packer_2d.py --datos data/datos_entrada_kiwi_arrow.xlsx
python3 src/modelo_prestow.py --datos data/datos_entrada_kiwi_arrow.xlsx --limite 180

# Correr la web (cuando exista)
streamlit run app/app.py
```

## Cómo trabajar con Claude Code

Este repositorio incluye `CLAUDE.md` en la raíz, que Claude Code carga automáticamente al abrir una sesión en la carpeta. Contiene el estado del proyecto y las reglas de trabajo.

Los prompts de Claude Code se redactan desde una conversación separada (donde se lleva el contexto ampliado del proyecto) y se pegan aquí para ejecución. Cada prompt debe:

1. Referirse a `CLAUDE.md` cuando corresponda.
2. Definir criterios de aceptación verificables.
3. No pedir cambios al núcleo (`modelo_prestow.py`, `packer_2d.py`) sin justificación explícita.

## Verificación del caso base

Cualquier corrida del núcleo debe reproducir:

| Métrica | Valor esperado |
|---|---|
| Unidades totales | 29.332 |
| Toneladas totales | 59.197 |
| Overstowage | 0 casos en 85 capas |
| Makespan (modelo) | ~58,19 h |
| Makespan (plan manual, en cálculo del modelo) | 60,61 h con error 0,01 h |

Si un test falla en cualquiera de estas cifras, revisar el test antes que el modelo.
