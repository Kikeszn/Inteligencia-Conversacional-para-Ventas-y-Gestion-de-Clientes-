import streamlit as st
from airtable_client import crear_lead, actualizar_lead, leer_leads_pendientes

st.title("Prueba de tubería — CRM Hackathon")

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
                "justificacion_score": "Prueba de tubería desde Streamlit",
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