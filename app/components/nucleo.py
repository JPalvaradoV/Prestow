"""
Mantiene el núcleo (src/) al día con el código en disco.

POR QUÉ HACE FALTA: Streamlit Community Cloud aplica cada push sin reiniciar
el proceso y solo recarga los módulos que vigila: los de app/ (la carpeta
del script principal) y los que están en PYTHONPATH. src/ se agrega con
sys.path.insert, así que Streamlit no lo vigila. Tras un push, las páginas se
actualizan pero api.py, modelo_prestow.py, etc. siguen en la versión vieja en
memoria. Pasó el 24-sep-2026: la página Ejecutar nueva le pasaba
nombre_buque a un resolver_prestow viejo → TypeError, hasta hacer "Reboot
app". Localmente pasa lo mismo si se edita src/ con la app corriendo.

asegurar_nucleo_actualizado() compara una firma (mtime y tamaño) de los .py
de src/ con la que quedó guardada al importar, y si cambió recarga los
módulos en orden de dependencias. Se llama al inicio de cada página.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_DIR_SRC = Path(__file__).resolve().parent.parent.parent / "src"

# Orden de recarga: cada módulo después de los que importa.
_ORDEN_RECARGA = [
    "modelo_prestow",
    "packer_2d",
    "solucion_inicial",
    "api",
    "layout_capa",
    "secuencia_izadas",
    "balance_peso",
]

# La firma se guarda en sys (no en este módulo): Streamlit sí recarga los
# módulos de app/, y con ellos se perdería una variable de módulo.
_ATRIBUTO_FIRMA = "_prestow_firma_nucleo"


def _firma_actual() -> tuple:
    return tuple(
        (p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(_DIR_SRC.glob("*.py"))
    )


def asegurar_nucleo_actualizado() -> list[str]:
    """
    Recarga los módulos de src/ ya importados si algún archivo de src/
    cambió desde la última vez. Devuelve los nombres recargados (vacío si no
    hizo falta).

    No recarga mientras hay una corrida del solver en curso (api._lock
    tomado): recargar api crea un lock nuevo y dos corridas podrían pisarse
    los globales de modelo_prestow. En ese caso se reintenta en la próxima
    carga de página.
    """
    firma = _firma_actual()
    anterior = getattr(sys, _ATRIBUTO_FIRMA, None)
    # Sin firma guardada (primera llamada del proceso) se recarga igual lo que
    # ya esté importado: no hay forma de saber de qué versión es. Cubre un
    # proceso que importó src/ antes de que existiera este chequeo, y cuesta
    # una sola recarga por proceso.
    if anterior is not None and firma == anterior:
        return []

    api = sys.modules.get("api")
    if api is not None and getattr(api, "_lock", None) is not None and api._lock.locked():
        return []

    recargados = []
    for nombre in _ORDEN_RECARGA:
        modulo = sys.modules.get(nombre)
        if modulo is not None:
            importlib.reload(modulo)
            recargados.append(nombre)
    setattr(sys, _ATRIBUTO_FIRMA, firma)
    return recargados
