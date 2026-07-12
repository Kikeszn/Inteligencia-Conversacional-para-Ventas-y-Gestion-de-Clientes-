import datetime

import streamlit as st

from airtable_client import actualizar_lead, crear_lead, leer_leads_pendientes
from llm_client import enviar_mensaje_tutor, iniciar_chat_tutor
from prompts.quiz_fijo import calificar_quiz, obtener_quiz
from prompts.tutor_prompt import construir_prompt_concepto

st.title("Tutor IA — Futuro Academy")

CONCEPTO_DEMO = "interes compuesto"

# La conversacion del Tutor avanza en pasos fijos guardados en session_state:
# inicio -> explicacion -> quiz -> consentimiento -> transferido
if "paso_tutor" not in st.session_state:
    st.session_state["paso_tutor"] = "inicio"

# --- Paso 1: iniciar la tutoria y pedir la explicacion al modelo ---
if st.session_state["paso_tutor"] == "inicio":
    nombre_usuario = st.text_input("¿Como te llamas?", value="Usuario Demo")
    if st.button("Empezar tutoria"):
        try:
            record_id = crear_lead(nombre_usuario)
            st.session_state["lead_id"] = record_id
            st.session_state["nombre_usuario"] = nombre_usuario

            chat = iniciar_chat_tutor()
            explicacion = enviar_mensaje_tutor(
                chat, construir_prompt_concepto(CONCEPTO_DEMO)
            )
            st.session_state["chat_tutor"] = chat
            st.session_state["explicacion"] = explicacion
            st.session_state["paso_tutor"] = "explicacion"
            st.rerun()
        except Exception as e:
            st.error(f"Error al iniciar la tutoria: {e}")

# --- Paso 2: mostrar la explicacion generada y pasar al quiz ---
elif st.session_state["paso_tutor"] == "explicacion":
    st.markdown(st.session_state["explicacion"])
    if st.button("Hacer el quiz"):
        st.session_state["paso_tutor"] = "quiz"
        st.rerun()

# --- Paso 3: quiz fijo (definido en codigo, no generado por el LLM) ---
elif st.session_state["paso_tutor"] == "quiz":
    st.subheader("Quiz rapido — 3 preguntas")
    preguntas = obtener_quiz(CONCEPTO_DEMO)
    respuestas = []
    for i, p in enumerate(preguntas):
        eleccion = st.radio(p["pregunta"], p["opciones"], key=f"pregunta_{i}", index=None)
        respuestas.append(p["opciones"].index(eleccion) if eleccion is not None else -1)

    if st.button("Enviar respuestas"):
        if -1 in respuestas:
            st.warning("Responde las 3 preguntas antes de continuar")
        else:
            resultado = calificar_quiz(CONCEPTO_DEMO, respuestas)
            try:
                actualizar_lead(st.session_state["lead_id"], {
                    "tema_interes_inicial": CONCEPTO_DEMO,
                    "resultado_quiz": resultado["resumen_texto"],
                    "fuente_contenido": "Futuro Academy — Modulo de Fundamentos de Inversion",
                })
                st.session_state["paso_tutor"] = "consentimiento"
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar el quiz: {e}")

# --- Paso 4: gate de consentimiento explicito ---
elif st.session_state["paso_tutor"] == "consentimiento":
    st.write(
        "¿Te parece si guardo tus respuestas para que un asesor te "
        "contacte con una propuesta personalizada?"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Si, adelante"):
            try:
                actualizar_lead(st.session_state["lead_id"], {
                    "consentimiento": True,
                    "fecha_consent": datetime.datetime.now().isoformat(),
                    "estado_tecnico": "Transferido",
                })
                st.session_state["paso_tutor"] = "transferido"
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar el consentimiento: {e}")
    with col2:
        if st.button("No, gracias"):
            st.session_state["paso_tutor"] = "sin_consentimiento"
            st.rerun()

elif st.session_state["paso_tutor"] == "transferido":
    st.success(
        "¡Gracias! Un asesor comercial va a revisar tu caso. "
        "(Aqui se dispararia el handoff al Agente Comercial — bloque 5)."
    )

elif st.session_state["paso_tutor"] == "sin_consentimiento":
    st.info(
        "Sin problema, no vamos a guardar tus datos comerciales. "
        "Puedes seguir aprendiendo cuando quieras."
    )

st.divider()

with st.expander("Pruebas de tuberia (bloque 2 — Airtable)"):
    if st.button("1. Crear lead de prueba"):
        try:
            record_id = crear_lead("Usuario Prueba")
            st.session_state["ultimo_id"] = record_id
            st.success(f"Lead creado: {record_id}")
        except Exception as e:
            st.error(f"Error al crear: {e}")

    if st.button("2. Actualizar lead de prueba"):
        if "ultimo_id" not in st.session_state:
            st.warning("Primero crea un lead")
        else:
            try:
                actualizar_lead(st.session_state["ultimo_id"], {
                    "prioridad": "Alta",
                    "justificacion_score": "Prueba de tuberia desde Streamlit",
                    "estado_tecnico": "Esperando Aprobacion",
                })
                st.success("Lead actualizado")
            except Exception as e:
                st.error(f"Error al actualizar: {e}")

    if st.button("3. Ver leads pendientes"):
        try:
            pendientes = leer_leads_pendientes()
            st.write(f"Encontrados: {len(pendientes)}")
            st.json(pendientes)
        except Exception as e:
            st.error(f"Error al leer: {e}")