"""
Test de app/components/nucleo.py: tras un push, Streamlit Cloud no recarga
src/ (24-sep-2026: TypeError por un resolver_prestow viejo en memoria).
"""

import inspect
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import api  # noqa: E402
from components.nucleo import asegurar_nucleo_actualizado  # noqa: E402


def test_recarga_src_cuando_cambia_un_archivo():
    asegurar_nucleo_actualizado()

    def viejo(ruta_datos, limite_segundos=180):
        raise AssertionError("api viejo")

    sys.modules["api"].resolver_prestow = viejo
    # Sin cambios en disco no recarga: sigue el "viejo"
    assert asegurar_nucleo_actualizado() == []
    assert sys.modules["api"].resolver_prestow is viejo

    ruta = Path(api.__file__)
    st = ruta.stat()
    os.utime(ruta, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    try:
        recargados = asegurar_nucleo_actualizado()
    finally:
        os.utime(ruta, ns=(st.st_atime_ns, st.st_mtime_ns))
        asegurar_nucleo_actualizado()
    assert "api" in recargados and "modelo_prestow" in recargados
    parametros = inspect.signature(sys.modules["api"].resolver_prestow).parameters
    assert "nombre_buque" in parametros
