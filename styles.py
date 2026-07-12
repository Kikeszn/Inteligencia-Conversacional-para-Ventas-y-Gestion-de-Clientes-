"""
Cargador de estilos personalizados. Unico archivo que sabe COMO se
inyecta CSS en Streamlit (via st.markdown + unsafe_allow_html). El
CSS en si vive en static/style.css como un archivo .css normal, para
que se pueda editar sin tocar codigo Python ni buscarlo escondido
dentro de un string largo en app.py.
"""

from pathlib import Path

import streamlit as st

# Esta línea arma la ruta completa hacia el archivo style.css, para que Python sepa exactamente dónde buscarlo
_RUTA_CSS = Path(__file__).parent / "static" / "style.css"


def cargar_css(ruta: Path = _RUTA_CSS) -> None:
    """Lee el archivo .css indicado y lo inyecta en la pagina actual
    de Streamlit. Si el archivo no existe, no rompe la app -- solo
    se queda sin estilos personalizados."""
    try:
        css = ruta.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass