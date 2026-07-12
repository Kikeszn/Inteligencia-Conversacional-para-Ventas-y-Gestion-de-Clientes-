import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from airtable_client import (
    actualizar_lead, crear_lead, leer_leads_pendientes
)

from llm_client import (
    clasificar_intencion,
    enviar_mensaje_comercial,
    enviar_mensaje_tutor,
    extraer_resumen_comercial,
    extraer_tema_interes,
    generar_prompt_datos_negocio,
    generar_quiz_tutor,
    iniciar_chat_comercial,
    iniciar_chat_tutor,
)

from prompts.quiz import calificar_quiz
from styles import cargar_css

cargar_css()

st.title("Asistente Future Academy")

# =========================================================================
# INICIALIZACIÓN DE ESTADOS
# =========================================================================
VALORES_INICIALES_SESSION_STATE = {
    "estado_ui": "pedir_nombre",
    "lead_id": None,
    "nombre_usuario": "",
    "historial_unificado": [],  # Guarda el chat completo independientemente del agente
    "chat_tutor": None,
    "chat_comercial": None,
    "turno_comercial": 0,
    "ultimo_agente": None,  # Rastrea quién respondió el último mensaje
    "datos_negocio_preguntados": False,
    "mensaje_pendiente_comercial": "",
    "resultado_quiz_temp": None,
    "quiz_preguntas_temp": None,
    "fuente_contenido_temp": None,
    "consentimiento_tutor_resultado": None,
    "resumen_generado": None,
    "ultimo_id": None,
    "tema_interes": None,  # Tema central de interes del usuario (1 a 4 palabras)
}

for _clave, _valor in VALORES_INICIALES_SESSION_STATE.items():
    if _clave not in st.session_state:
        st.session_state[_clave] = _valor

# =========================================================================
# PANTALLA 1: REGISTRO INICIAL
# =========================================================================
if st.session_state["estado_ui"] == "pedir_nombre":
    nombre = st.text_input("¿Cómo te llamas?")
    if st.button("Comenzar Chat"):
        if not nombre.strip():
            st.warning("Escribe tu nombre antes de continuar.")
        else:
            try:
                lead_id = crear_lead(nombre)
                st.session_state["lead_id"] = lead_id
                st.session_state["nombre_usuario"] = nombre

                # Inicializar ambas memorias de IA en segundo plano
                st.session_state["chat_tutor"] = iniciar_chat_tutor()
                st.session_state["chat_comercial"] = iniciar_chat_comercial()

                # Mensaje de bienvenida del sistema unificado
                msg_bienvenida = f"¡Hola, {nombre}! Soy tu asistente de Future Academy. ¿En qué te puedo ayudar hoy?"
                st.session_state["historial_unificado"].append({"rol": "assistant", "contenido": msg_bienvenida})

                st.session_state["estado_ui"] = "chat_libre"
                st.rerun()
            except Exception as e:
                st.error(f"Error al iniciar: {e}")

# =========================================================================
# PANTALLA 2: INTERFAZ DE CHAT UNIFICADA (LA "CAJA NEGRA")
# =========================================================================
elif st.session_state["estado_ui"] == "chat_libre":

    # 1. Renderizar todo el historial de la conversación
    for msg in st.session_state["historial_unificado"]:
        with st.chat_message(msg["rol"]):
            st.markdown(msg["contenido"])

    # 2. Opciones Contextuales (Ej: Mostrar botón de Quiz si el Tutor acaba de hablar)
    if st.session_state["ultimo_agente"] == "tutor":
        if st.button("Hacer un quiz rápido sobre esto", key="btn_hacer_quiz"):
            st.session_state["estado_ui"] = "quiz_tutor"
            st.rerun()

    # 3. Input dinámico: Se evalúa CADA vez que el usuario escribe
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):

        # Mostrar el mensaje del usuario inmediatamente
        st.session_state["historial_unificado"].append({"rol": "user", "contenido": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- AQUÍ VIVE EL ENRUTADOR DINÁMICO ---
        with st.spinner("Pensando..."):
            agente_destino = clasificar_intencion(prompt)
            st.session_state["ultimo_agente"] = agente_destino

            if agente_destino == "tutor":
                # Derivar al modelo tutor de forma transparente
                respuesta = enviar_mensaje_tutor(st.session_state["chat_tutor"], prompt)
                st.session_state["historial_unificado"].append({"rol": "assistant", "contenido": respuesta})
                st.rerun()

            elif agente_destino == "comercial":
                # Derivar al modelo comercial
                if not st.session_state["datos_negocio_preguntados"]:
                    # Interrupción: Es la primera vez que detectamos intención comercial.
                    # Guardamos el mensaje en pausa y pedimos consentimiento.
                    st.session_state["mensaje_pendiente_comercial"] = prompt
                    st.session_state["estado_ui"] = "preguntar_datos_negocio"
                    st.rerun()
                else:
                    # Chat comercial continuo
                    respuesta = enviar_mensaje_comercial(st.session_state["chat_comercial"], prompt)
                    st.session_state["historial_unificado"].append({"rol": "assistant", "contenido": respuesta})
                    st.session_state["turno_comercial"] += 1

                    # Validar el límite de turnos comerciales
                    if st.session_state["turno_comercial"] >= 3:
                        st.session_state["estado_ui"] = "resumen_comercial"

                    st.rerun()

# =========================================================================
# PANTALLAS DE INTERRUPCIÓN (Formularios, Quizzes y Cierres)
# =========================================================================

# --- FLUJO TUTOR: QUIZ Y CONSENTIMIENTO ---
elif st.session_state["estado_ui"] == "quiz_tutor":
    st.subheader("Quiz rápido")

    # El quiz lo genera el Tutor en base a lo hablado en el chat, no un
    # cuestionario fijo. Se genera una sola vez por intento y se guarda en
    # sesión para no volver a llamar al modelo en cada rerun del formulario.
    if st.session_state["quiz_preguntas_temp"] is None:
        with st.spinner("Generando tu quiz..."):
            historial_texto = "\n".join(
                [f"{msg['rol']}: {msg['contenido']}" for msg in st.session_state["historial_unificado"]]
            )
            st.session_state["quiz_preguntas_temp"] = generar_quiz_tutor(historial_texto)
            st.session_state["tema_interes"] = extraer_tema_interes(historial_texto)

    preguntas = st.session_state["quiz_preguntas_temp"]
    respuestas = []

    for i, p in enumerate(preguntas):
        eleccion = st.radio(p["pregunta"], p["opciones"], key=f"pregunta_{i}", index=None)
        respuestas.append(p["opciones"].index(eleccion) if eleccion is not None else -1)

    if st.button("Enviar respuestas"):
        if -1 in respuestas:
            st.warning("Responde las 3 preguntas antes de continuar")
        else:
            resultado = calificar_quiz(preguntas, respuestas)
            st.session_state["resultado_quiz_temp"] = resultado["resumen_texto"]
            st.session_state["fuente_contenido_temp"] = "Future Academy -- Módulo de Fundamentos de Inversión"
            st.session_state["quiz_preguntas_temp"] = None
            st.session_state["estado_ui"] = "consentimiento_tutor"
            st.rerun()

elif st.session_state["estado_ui"] == "consentimiento_tutor":
    st.write("¿Te parece si guardo tus respuestas para que un asesor te contacte con una propuesta personalizada?")

    # No se puede anidar un st.button dentro del "if" de otro st.button: en el
    # rerun que dispara el segundo botón, el primero vuelve a evaluar False y
    # ese bloque completo se salta, así que la navegación nunca se ejecuta.
    # Por eso el resultado del consentimiento se guarda en session_state y el
    # botón "Volver al chat" se renderiza en un paso aparte.
    if st.session_state["consentimiento_tutor_resultado"] is None:
        col1, col2 = st.columns(2)

        if col1.button("Sí, adelante"):
            try:
                actualizar_lead(st.session_state["lead_id"], {
                    "tema_interes_inicial": st.session_state["tema_interes"],
                    "resultado_quiz": st.session_state["resultado_quiz_temp"],
                    "fuente_contenido": st.session_state["fuente_contenido_temp"],
                    "consentimiento": True,
                    "fecha_consent": datetime.datetime.now(ZoneInfo("America/Guayaquil")).isoformat(),
                    "estado_tecnico": "Transferido",
                })
                st.session_state["consentimiento_tutor_resultado"] = "aceptado"
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar el consentimiento: {e}")

        if col2.button("No, gracias"):
            st.session_state["consentimiento_tutor_resultado"] = "rechazado"
            st.rerun()
    else:
        if st.session_state["consentimiento_tutor_resultado"] == "aceptado":
            st.success("¡Gracias! Un asesor comercial va a revisar tu caso.")
        else:
            st.info("Sin problema. Puedes seguir aprendiendo cuando quieras.")

        if st.button("Volver al chat"):
            st.session_state["consentimiento_tutor_resultado"] = None
            st.session_state["estado_ui"] = "chat_libre"
            st.rerun()

# --- FLUJO COMERCIAL: CONSENTIMIENTO Y FORMULARIO ---
elif st.session_state["estado_ui"] == "preguntar_datos_negocio":
    st.write(
        "Antes de continuar: ¿te parece si compartes algunos datos generales de tu negocio (ingresos, activos, deudas)? Esto nos ayuda a darte una recomendación más precisa.")
    col1, col2 = st.columns(2)

    if col1.button("Sí, compartir datos"):
        st.session_state["estado_ui"] = "formulario_negocio"
        st.rerun()

    if col2.button("Prefiero no compartir"):
        st.session_state["datos_negocio_preguntados"] = True
        with st.spinner("Procesando tu consulta..."):
            # Enviar el mensaje que se había quedado en pausa
            respuesta = enviar_mensaje_comercial(
                st.session_state["chat_comercial"],
                st.session_state["mensaje_pendiente_comercial"]
            )
            st.session_state["historial_unificado"].append({"rol": "assistant", "contenido": respuesta})
            st.session_state["turno_comercial"] += 1
            actualizar_lead(st.session_state["lead_id"], {"datos_negocio_compartidos": False})
            st.session_state["estado_ui"] = "chat_libre"
            st.rerun()

elif st.session_state["estado_ui"] == "formulario_negocio":
    st.subheader("Información del negocio")
    with st.form("form_datos_negocio"):
        ingresos_dia = st.number_input("Ingresos por día (en promedio)", min_value=0.0, step=10.0)
        ingresos_mes = st.number_input("Ingresos al mes (en promedio)", min_value=0.0, step=50.0)
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            total_activos = st.number_input("Total de activos", min_value=0.0, step=100.0)
            total_deudas = st.number_input("Total en deudas o créditos", min_value=0.0, step=100.0)
        with col2:
            total_pasivos = st.number_input("Total de pasivos", min_value=0.0, step=100.0)
            total_prestamos = st.number_input("Total en préstamos", min_value=0.0, step=100.0)
        enviado = st.form_submit_button("Enviar información")

    if enviado:
        datos_negocio = {
            "ingresos_dia": ingresos_dia, "ingresos_mes": ingresos_mes,
            "total_activos": total_activos, "total_pasivos": total_pasivos,
            "total_deudas": total_deudas, "total_prestamos": total_prestamos,
        }
        st.session_state["datos_negocio"] = datos_negocio
        st.session_state["datos_negocio_preguntados"] = True

        contexto = generar_prompt_datos_negocio(datos_negocio)
        mensaje_combinado = f"{st.session_state['mensaje_pendiente_comercial']}\n\n{contexto}"

        with st.spinner("Procesando información..."):
            respuesta = enviar_mensaje_comercial(st.session_state["chat_comercial"], mensaje_combinado)
            st.session_state["historial_unificado"].append({"rol": "assistant", "contenido": respuesta})
            st.session_state["turno_comercial"] += 1

            actualizar_lead(st.session_state["lead_id"], {
                "datos_negocio_compartidos": True,
                **datos_negocio,
            })
            st.session_state["estado_ui"] = "chat_libre"
            st.rerun()

# --- CIERRE COMERCIAL: RESUMEN Y BLOQUEO ---
elif st.session_state["estado_ui"] == "resumen_comercial":
    st.info("Generando resumen del caso...")

    if st.session_state["resumen_generado"] is None:
        #Convertimos todo el historial unificado en texto plano para el extractor
        historial_texto = "\n".join(
            [f"{msg['rol']}: {msg['contenido']}" for msg in st.session_state["historial_unificado"]])
        resumen = extraer_resumen_comercial(historial_texto)

        try:
            actualizar_lead(st.session_state["lead_id"], {
                "tipo_prospecto": resumen.get("tipo_prospecto", ""),
                "resumen_necesidad": resumen.get("resumen_necesidad", ""),
                "objeciones": resumen.get("objeciones", ""),
                "etapa_embudo": resumen.get("etapa_embudo", "Descubrimiento"),
                "prioridad": resumen.get("prioridad", "Media"),
                "justificacion_score": resumen.get("justificacion_score", ""),
                "accion_sugerida": resumen.get("accion_sugerida", ""),
                "estado_tecnico": "Esperando Aprobacion",
            })
            st.session_state["resumen_generado"] = resumen
        except Exception as e:
            st.error(f"Error al guardar el resumen: {e}")

    if st.session_state["resumen_generado"] is not None:
        st.success("¡Gracias! Un asesor humano va a revisar tu caso para contactarte.")