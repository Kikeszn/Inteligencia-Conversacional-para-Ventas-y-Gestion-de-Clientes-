import datetime

import streamlit as st

from airtable_client import actualizar_lead, crear_lead, leer_leads_pendientes
from llm_client import (
    clasificar_intencion,
    enviar_mensaje_comercial,
    enviar_mensaje_tutor,
    extraer_resumen_comercial,
    generar_prompt_datos_negocio,
    iniciar_chat_comercial,
    iniciar_chat_tutor,
)
from prompts.quiz_fijo import calificar_quiz, obtener_quiz

st.title("Asistente Futuro Academy")

CONCEPTO_DEMO = "interes compuesto"

# Estado general: 'agente_activo' queda en None hasta que el enrutador
# clasifica el primer mensaje. A partir de ahi, cada agente sigue su
# propia maquina de estados (paso_tutor / paso_comercial).
if "agente_activo" not in st.session_state:
    st.session_state["agente_activo"] = None

# =========================================================================
# PASO 0: Entrada unica -- el usuario NO elige agente, solo escribe
# =========================================================================
if st.session_state["agente_activo"] is None:
    nombre_usuario = st.text_input("Como te llamas?", value="Usuario Demo")
    mensaje_inicial = st.text_area(
        "En que te puedo ayudar?",
        placeholder="Ej: 'quiero aprender sobre invertir' o 'quiero un asesor para mi empresa'",
    )

    if st.button("Enviar"):
        if not mensaje_inicial.strip():
            st.warning("Escribe tu mensaje antes de continuar")
        else:
            try:
                lead_id = crear_lead(nombre_usuario)
                st.session_state["lead_id"] = lead_id
                st.session_state["nombre_usuario"] = nombre_usuario

                # --- Aqui vive el Agente Enrutador ---
                agente = clasificar_intencion(mensaje_inicial)
                st.session_state["agente_activo"] = agente

                if agente == "tutor":
                    chat = iniciar_chat_tutor()
                    explicacion = enviar_mensaje_tutor(chat, mensaje_inicial)
                    st.session_state["chat_tutor"] = chat
                    st.session_state["explicacion"] = explicacion
                    st.session_state["paso_tutor"] = "explicacion"
                else:  # comercial
                    st.session_state["chat_comercial"] = iniciar_chat_comercial()
                    st.session_state["mensaje_inicial_comercial"] = mensaje_inicial
                    st.session_state["paso_comercial"] = "preguntar_consentimiento"

                st.rerun()
            except Exception as e:
                st.session_state["agente_activo"] = None
                st.error(f"Error al iniciar la conversacion: {e}")

# =========================================================================
# FLUJO DEL TUTOR (Historia 2)
# =========================================================================
elif st.session_state["agente_activo"] == "tutor":
    st.caption("Te estamos atendiendo con el Tutor IA de Futuro Academy")

    if st.session_state["paso_tutor"] == "explicacion":
        st.markdown(st.session_state["explicacion"])
        if st.button("Hacer el quiz"):
            st.session_state["paso_tutor"] = "quiz"
            st.rerun()

    elif st.session_state["paso_tutor"] == "quiz":
        st.subheader("Quiz rapido -- 3 preguntas")
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
                        "fuente_contenido": "Futuro Academy -- Modulo de Fundamentos de Inversion",
                    })
                    st.session_state["paso_tutor"] = "consentimiento"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar el quiz: {e}")

    elif st.session_state["paso_tutor"] == "consentimiento":
        st.write(
            "Te parece si guardo tus respuestas para que un asesor te "
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
        st.success("Gracias! Un asesor comercial va a revisar tu caso.")

    elif st.session_state["paso_tutor"] == "sin_consentimiento":
        st.info(
            "Sin problema, no vamos a guardar tus datos comerciales. "
            "Puedes seguir aprendiendo cuando quieras."
        )

# =========================================================================
# FLUJO DEL COMERCIAL (Historia 1 y 3)
# =========================================================================
elif st.session_state["agente_activo"] == "comercial":
    st.caption("Te estamos atendiendo con el Agente Comercial")

    # --- Paso A: preguntar si quiere compartir datos del negocio ---
    if st.session_state["paso_comercial"] == "preguntar_consentimiento":
        st.write(
            "Antes de continuar: te parece si compartes algunos datos "
            "generales de tu negocio (ingresos, activos, deudas)? Esto "
            "nos ayuda a darte una recomendacion mas precisa y rapida."
        )
        col1, col2 = st.columns(2)
        with col1:
            compartir = st.button("Si, compartir datos")
        with col2:
            no_compartir = st.button("Prefiero no compartir")

        if compartir:
            st.session_state["paso_comercial"] = "formulario"
            st.rerun()

        if no_compartir:
            try:
                respuesta = enviar_mensaje_comercial(
                    st.session_state["chat_comercial"],
                    st.session_state["mensaje_inicial_comercial"],
                )
                st.session_state["historial_comercial"] = [
                    f"Usuario: {st.session_state['mensaje_inicial_comercial']}",
                    f"Comercial: {respuesta}",
                ]
                st.session_state["turno_comercial"] = 1
                actualizar_lead(st.session_state["lead_id"], {
                    "datos_negocio_compartidos": False,
                })
                st.session_state["paso_comercial"] = "chat"
                st.rerun()
            except Exception as e:
                st.error(f"Error al iniciar la conversacion comercial: {e}")

    # --- Paso B: formulario de datos del negocio ---
    elif st.session_state["paso_comercial"] == "formulario":
        st.subheader("Informacion del negocio")
        with st.form("form_datos_negocio"):
            ingresos_dia = st.number_input("Ingresos por dia (en promedio)", min_value=0.0, step=10.0)
            ingresos_mes = st.number_input("Ingresos al mes (en promedio)", min_value=0.0, step=50.0)
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                total_activos = st.number_input("Total de activos", min_value=0.0, step=100.0)
                total_deudas = st.number_input("Total en deudas o creditos", min_value=0.0, step=100.0)
            with col2:
                total_pasivos = st.number_input("Total de pasivos", min_value=0.0, step=100.0)
                total_prestamos = st.number_input("Total en prestamos", min_value=0.0, step=100.0)
            enviado = st.form_submit_button("Enviar informacion")

        if enviado:
            datos_negocio = {
                "ingresos_dia": ingresos_dia,
                "ingresos_mes": ingresos_mes,
                "total_activos": total_activos,
                "total_pasivos": total_pasivos,
                "total_deudas": total_deudas,
                "total_prestamos": total_prestamos,
            }
            st.session_state["datos_negocio"] = datos_negocio

            contexto = generar_prompt_datos_negocio(datos_negocio)
            mensaje_con_contexto = (
                f"{st.session_state['mensaje_inicial_comercial']}\n\n{contexto}"
            )

            try:
                respuesta = enviar_mensaje_comercial(
                    st.session_state["chat_comercial"], mensaje_con_contexto
                )
                st.session_state["historial_comercial"] = [
                    f"Usuario: {st.session_state['mensaje_inicial_comercial']}",
                    "Usuario: (comparte datos financieros de su negocio via formulario)",
                    f"Comercial: {respuesta}",
                ]
                st.session_state["turno_comercial"] = 1

                actualizar_lead(st.session_state["lead_id"], {
                    "datos_negocio_compartidos": True,
                    **datos_negocio,
                })

                st.session_state["paso_comercial"] = "chat"
                st.rerun()
            except Exception as e:
                st.error(f"Error al procesar el formulario: {e}")

    # --- Paso C: chat comercial normal ---
    elif st.session_state["paso_comercial"] == "chat":
        for linea in st.session_state["historial_comercial"]:
            st.write(linea)

        if st.session_state["turno_comercial"] < 3:
            siguiente_mensaje = st.text_input("Tu respuesta", key="input_comercial")
            if st.button("Responder"):
                if siguiente_mensaje.strip():
                    try:
                        respuesta = enviar_mensaje_comercial(
                            st.session_state["chat_comercial"], siguiente_mensaje
                        )
                        st.session_state["historial_comercial"].append(f"Usuario: {siguiente_mensaje}")
                        st.session_state["historial_comercial"].append(f"Comercial: {respuesta}")
                        st.session_state["turno_comercial"] += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al enviar el mensaje: {e}")
        else:
            st.info("Se alcanzo el limite de 3 intercambios. Generando resumen...")
            if "resumen_generado" not in st.session_state:
                historial_texto = "\n".join(st.session_state["historial_comercial"])
                resumen = extraer_resumen_comercial(historial_texto)
                try:
                    actualizar_lead(st.session_state["lead_id"], {
                        "tipo_prospecto": resumen.get("tipo_prospecto", "B2C"),
                        "resumen_necesidad": resumen.get("resumen_necesidad", ""),
                        "objeciones": resumen.get("objeciones", ""),
                        "etapa_embudo": resumen.get("etapa_embudo", "Descubrimiento"),
                        "prioridad": resumen.get("prioridad", "Media"),
                        "justificacion_score": resumen.get("justificacion_score", ""),
                        "accion_sugerida": resumen.get("accion_sugerida", "Derivar a especialista"),
                        "estado_tecnico": "Esperando Aprobacion",
                    })
                    st.session_state["resumen_generado"] = resumen
                except Exception as e:
                    st.error(f"Error al guardar el resumen: {e}")

            if "resumen_generado" in st.session_state:
                st.success("Gracias! Un asesor va a revisar tu caso.")
                st.json(st.session_state["resumen_generado"])
                if "datos_negocio" in st.session_state:
                    st.caption("Datos financieros del negocio compartidos:")
                    st.json(st.session_state["datos_negocio"])

st.divider()

with st.expander("Pruebas de tuberia (bloque 2 -- Airtable)"):
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