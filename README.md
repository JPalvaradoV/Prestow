# Prestow Lirquén — Optimización del plan de estiba

Herramienta de optimización del prestow de celulosa unitizada en buques open hatch, caso base **Kiwi Arrow** en Puerto Lirquén.

**Contexto:** Capstone Analytics 2026-02, Ingeniería UDD. 5 personas, 7 semanas + 1 de colchón.

## Estado

El modelo MILP está implementado, corrido y validado (tres pasadas lexicográficas: makespan → izadas+fragmentación → balance de peso). Con capacidad real por plan (dato verificado del puerto donde existe), el makespan del caso base es **≈59,67 h** — ver `CLAUDE.md` sección 3 antes de citar cualquier otra cifra.

La **página web (Streamlit)** está construida hasta Fase 2: configuración editable del buque/productos/viaje/rotación, ejecución del modelo, y resultados (planimetría tipo prestow, KPIs, izadas como bloques rectangulares, balance de peso). Lista para desplegar en Streamlit Community Cloud (ver "Despliegue" más abajo). Detalle completo en `docs/05_Estado_app_web.md`.

## Estructura

```
prestow-lirquen/
├── CLAUDE.md              # Contexto operacional para Claude Code (auto-cargado)
├── README.md              # Este archivo
├── requirements.txt     # Dependencias de ejecución (las que instala Streamlit Cloud)
├── requirements-dev.txt # + pytest, black, ruff, mypy
├── pyproject.toml
├── .gitignore
│
├── src/                   # Núcleo de optimización
│   ├── modelo_prestow.py  # Modelo MILP completo (3 pasadas lexicográficas)
│   ├── packer_2d.py       # Cálculo de capacidad geométrica
│   ├── api.py             # resolver_prestow() — función pura que llama la web
│   ├── layout_capa.py     # Posiciones (x, y, fila, columna) dentro de la capa
│   ├── secuencia_izadas.py# Agrupa en izadas de 16 como bloques rectangulares
│   ├── balance_peso.py    # Peso y densidad por bodega (informativo)
│   ├── extraer_capacidades_reales.py  # Extrae capacidad real por plan del puerto
│   └── stability_test.py  # 5 semillas para estabilidad
│
├── app/                   # Página web Streamlit (Fase 2 — falta probar en navegador y desplegar)
│   ├── app.py             # Entry point
│   ├── pages/             # Configuración, Ejecutar, Resultados
│   └── components/        # config_editable, vista_buque, formato, caso_demo, estilo
│
├── data/
│   ├── datos_entrada_kiwi_arrow.xlsx      # Caso base editable
│   ├── capacidades.csv                    # Salida del packer (geometría uniforme)
│   ├── capacidades_reales_por_plan.csv    # Capacidad real por (bodega, plan, producto)
│   ├── plan_estiba.xlsx                   # Salida de ejemplo del modelo
│   ├── stability_report.csv               # Salida de stability_test.py
│   └── raw/                               # Excels originales del puerto (git-ignored)
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
pip install -r requirements-dev.txt   # o requirements.txt si no se van a correr tests

# Correr el modelo por CLI
python3 src/packer_2d.py --datos data/datos_entrada_kiwi_arrow.xlsx
python3 src/modelo_prestow.py --datos data/datos_entrada_kiwi_arrow.xlsx --limite 180

# Correr la web
streamlit run app/app.py

# Tests
python -m pytest
```

## Despliegue (Streamlit Community Cloud)

1. En https://share.streamlit.io, "Create app" → "Deploy a public app from GitHub".
2. Repositorio `JPalvaradoV/Prestow`, rama `master`, archivo principal `app/app.py`.
3. En "Advanced settings", elegir Python 3.12 o superior (el proyecto pide >= 3.11).
4. Deploy. Streamlit Cloud instala `requirements.txt` (sin las dependencias de desarrollo) y toma el tema de `.streamlit/config.toml`.

La app no necesita secretos ni `data/raw/` (no versionado): usa solo los archivos versionados de `data/`. Cada sesión guarda sus datos editados en un directorio temporal propio, así que varios usuarios no se pisan. Las corridas del solver sí se encolan (un solo modelo a la vez por proceso, ver `_lock` en `src/api.py`). La app se duerme tras 12 h sin uso y despierta con la primera visita.

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
| Unidades totales | 29.332 (confirmado como PROGRAMA LQN, ver `CLAUDE.md` sección 10 #3) |
| Toneladas totales | 59.197 |
| Overstowage | 0 casos en 85 capas |
| Makespan (modelo, capacidad real por plan) | ~59,67 h — **no** 58,19 h, ver `CLAUDE.md` sección 3 |
| Makespan (plan manual, en cálculo del modelo) | 60,61 h; horas por cuadrilla con error máximo 0,023 h (re-validado el 22-sep-2026) |

Si un test falla en cualquiera de estas cifras, revisar el test antes que el modelo.

## Más contexto

- `CLAUDE.md` — estado operacional completo, decisiones cerradas, pendientes, qué no hacer.
- `docs/05_Estado_app_web.md` — estado detallado de la app Streamlit, fase por fase.
- Reportes de sesión en `docs/reportes_sesion/` — qué se hizo cada día de trabajo y por qué.
