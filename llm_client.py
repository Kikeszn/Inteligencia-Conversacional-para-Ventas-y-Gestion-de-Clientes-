"""
Cliente del modelo de lenguaje (Gemini). Solo llamadas al LLM — nada de
logica de Airtable ni de interfaz aqui, para respetar la separacion que
pide la rubrica.

Usa el SDK oficial actual `google-genai` (paquete: google-genai,
import: `from google import genai`). El paquete viejo
`google-generativeai` esta deprecado — si ven codigo de tutoriales de
2023-2024 que use `import google.generativeai as genai`, es la version
anterior; no la usen.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts.tutor_prompt import TUTOR_SYSTEM_PROMPT

load_dotenv()


def _obtener_api_key() -> str:
    """Busca la API key primero en variables de entorno (.env local) y,
    si no la encuentra, en st.secrets (Streamlit Cloud). Import de
    streamlit es local a la funcion para que este modulo tambien se
    pueda probar fuera de una app de Streamlit si hace falta."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception as exc:
        raise RuntimeError(
            "No se encontro GEMINI_API_KEY ni en .env ni en st.secrets"
        ) from exc


_client = genai.Client(api_key=_obtener_api_key())

_MODEL_NAME = "gemini-3.1-flash-lite"


def iniciar_chat_tutor():
    """Crea una sesion de chat nueva para el Tutor, con su system prompt
    ya cargado. Se llama una vez por conversacion y el objeto se guarda
    en st.session_state para mantener el historial entre turnos."""
    return _client.chats.create(
        model=_MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=TUTOR_SYSTEM_PROMPT,
        ),
    )


def enviar_mensaje_tutor(chat, mensaje: str) -> str:
    """Envia un mensaje a una sesion de chat del Tutor ya iniciada y
    devuelve el texto de la respuesta. Cualquier error de red o de API
    se propaga hacia arriba para que app.py decida como mostrarlo."""
    respuesta = chat.send_message(mensaje)
    return respuesta.text
