"""
Cliente del modelo de lenguaje (Gemini). Solo llamadas al LLM -- nada de
logica de Airtable ni de interfaz aqui, para respetar la separacion que
pide la rubrica.

Usa el SDK oficial actual google-genai (paquete: google-genai, import:
from google import genai).
"""

import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts.comercial_prompt import (
    COMERCIAL_EXTRACTOR_PROMPT,
    COMERCIAL_SYSTEM_PROMPT,
    construir_contexto_datos_negocio,
)
from prompts.quiz import QUIZ_FALLBACK
from prompts.router_prompt import ROUTER_PROMPT
from prompts.tutor_prompt import TUTOR_SYSTEM_PROMPT, construir_prompt_quiz

load_dotenv()


def _obtener_api_key() -> str:
    """Busca la API key primero en variables de entorno (.env local) y,
    si no la encuentra, en st.secrets (Streamlit Cloud)."""
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


# --- Agente Enrutador ---------------------------------------------------

def clasificar_intencion(mensaje_usuario: str) -> str:
    """Clasifica el primer mensaje del usuario como 'tutor' o
    'comercial'. Se llama UNA sola vez al inicio de la conversacion."""
    prompt = f"{ROUTER_PROMPT}\n\nMensaje del usuario: {mensaje_usuario}"
    try:
        respuesta = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        resultado = json.loads(respuesta.text)
        agente = resultado.get("agente", "tutor")
        return agente if agente in ("tutor", "comercial") else "tutor"
    except Exception:
        return "tutor"


# --- Agente Tutor ---------------------------------------------------

def iniciar_chat_tutor():
    return _client.chats.create(
        model=_MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=TUTOR_SYSTEM_PROMPT,
        ),
    )


def enviar_mensaje_tutor(chat, mensaje: str) -> str:
    respuesta = chat.send_message(mensaje)
    return respuesta.text


def _quiz_generado_es_valido(preguntas) -> bool:
    """Valida que el JSON que devolvio el modelo tenga exactamente 3
    preguntas, cada una con al menos 2 opciones y un indice 'correcta'
    valido dentro de esas opciones."""
    if not isinstance(preguntas, list) or len(preguntas) != 3:
        return False
    for pregunta in preguntas:
        if not isinstance(pregunta, dict):
            return False
        if not isinstance(pregunta.get("pregunta"), str) or not pregunta["pregunta"].strip():
            return False
        opciones = pregunta.get("opciones")
        if not isinstance(opciones, list) or len(opciones) < 2:
            return False
        correcta = pregunta.get("correcta")
        if not isinstance(correcta, int) or isinstance(correcta, bool) or not (0 <= correcta < len(opciones)):
            return False
    return True


def generar_quiz_tutor(historial_texto: str) -> list[dict]:
    """Le pide al Tutor (fuera del chat en curso, con una llamada aparte)
    que genere el quiz de 3 preguntas en base al historial completo de
    la conversacion. Si el modelo falla o devuelve una forma invalida,
    se usa el quiz de respaldo fijo para no romper el flujo."""
    prompt = construir_prompt_quiz(historial_texto)
    try:
        respuesta = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=TUTOR_SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        resultado = json.loads(respuesta.text)
        preguntas = resultado.get("preguntas", [])
        return preguntas if _quiz_generado_es_valido(preguntas) else QUIZ_FALLBACK
    except Exception:
        return QUIZ_FALLBACK


# --- Agente Comercial ---------------------------------------------------

def iniciar_chat_comercial():
    return _client.chats.create(
        model=_MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=COMERCIAL_SYSTEM_PROMPT,
        ),
    )


def enviar_mensaje_comercial(chat, mensaje: str) -> str:
    respuesta = chat.send_message(mensaje)
    return respuesta.text


def generar_prompt_datos_negocio(datos: dict) -> str:
    """Envoltura fina sobre construir_contexto_datos_negocio, disponible
    desde llm_client para quien importe desde aqui."""
    return construir_contexto_datos_negocio(datos)


def extraer_resumen_comercial(historial_texto: str) -> dict:
    """Al cerrar la conversacion comercial (tercer intercambio), le
    pide al modelo un resumen estructurado en JSON para guardar en
    Airtable. Si algo falla, devuelve valores por defecto."""
    prompt = f"{COMERCIAL_EXTRACTOR_PROMPT}\n{historial_texto}"
    try:
        respuesta = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(respuesta.text)
    except Exception:
        return {
            "tipo_prospecto": "B2C",
            "resumen_necesidad": "No se pudo generar el resumen automatico.",
            "objeciones": "N/A",
            "etapa_embudo": "Descubrimiento",
            "prioridad": "Media",
            "justificacion_score": "Error al procesar la respuesta del modelo.",
            "accion_sugerida": "Derivar a especialista",
        }