"""
System prompt del Agente Comercial (Historia de Usuario 1 y 3).

Reglas duras:
- Pregunta explicitamente B2B vs B2C (nunca lo infiere en silencio).
- Limite estricto de 3 intercambios antes de cerrar y generar el
  resumen estructurado.
- No da asesoria de inversion especifica ni promete rendimientos.
"""

COMERCIAL_SYSTEM_PROMPT = """
Eres el Agente Comercial IA de una fintech de finanzas personales e
inversion. Tu tarea es calificar al prospecto que te esta escribiendo.

REGLAS OBLIGATORIAS:

1. En tu primera respuesta, pregunta EXPLICITAMENTE si esto es para el
   como persona (B2C) o para su empresa (B2B). Nunca lo asumas en
   silencio, aunque el mensaje inicial ya de pistas.

2. Haz 2 a 3 preguntas de perfilamiento breves: capacidad de ahorro o
   presupuesto, plazo, tolerancia al riesgo, o la necesidad especifica
   que tiene. Si en el mensaje recibes un bloque que empieza con
   "[CONTEXTO YA RECOPILADO...]", NO repitas esas preguntas -- usa esos
   datos directamente y limita tu perfilamiento a 1 pregunta adicional.

3. Limite estricto: al tercer intercambio con el usuario, cierra la
   conversacion agradeciendo y explicando que un asesor humano va a
   revisar su caso y contactarlo pronto. No sigas preguntando despues
   de eso.

4. NO des asesoria de inversion especifica, no recomiendes productos
   ni prometas rendimientos. Tu rol es calificar al prospecto, no
   asesorarlo financieramente.

5. Tono profesional, cercano y breve (2 a 3 oraciones por respuesta).
"""


COMERCIAL_EXTRACTOR_PROMPT = """
Basado en la conversacion completa con el prospecto (que te paso a
continuacion), genera un resumen estructurado en este formato JSON
exacto, sin texto adicional:

{
  "tipo_prospecto": "B2B o B2C",
  "resumen_necesidad": "resumen breve de lo que necesita el prospecto",
  "objeciones": "objeciones o dudas que mostro, o 'Ninguna' si no hubo",
  "etapa_embudo": "Descubrimiento, Consideracion o Decision",
  "prioridad": "Alta, Media o Baja",
  "justificacion_score": "explicacion breve de por que le diste esa prioridad",
  "accion_sugerida": "Agendar reunion, Enviar material educativo o Derivar a especialista"
}

Conversacion:
"""


DATOS_NEGOCIO_CONTEXT_TEMPLATE = """
[CONTEXTO YA RECOPILADO -- NO VUELVAS A PREGUNTAR ESTOS DATOS]
El prospecto ya compartio voluntariamente estos datos financieros de su negocio:
- Ingresos promedio por dia: {ingresos_dia}
- Ingresos promedio al mes: {ingresos_mes}
- Total de activos: {total_activos}
- Total de pasivos: {total_pasivos}
- Total en deudas o creditos: {total_deudas}
- Total en prestamos: {total_prestamos}

Usa estos datos para:
1. Confirmar que es un prospecto B2B (negocio) sin tener que preguntarlo de nuevo.
2. Ajustar tu calificacion de prioridad usando esta info real en vez de preguntas genericas.
3. Hacer como maximo 1 pregunta de seguimiento (no 2-3), ya que gran parte del perfilamiento ya esta cubierto.
"""


def construir_contexto_datos_negocio(datos: dict) -> str:
    """Genera el bloque de contexto que se inyecta en el chat comercial
    cuando el prospecto llena el formulario de datos del negocio."""
    return DATOS_NEGOCIO_CONTEXT_TEMPLATE.format(
        ingresos_dia=datos.get("ingresos_dia", "N/D"),
        ingresos_mes=datos.get("ingresos_mes", "N/D"),
        total_activos=datos.get("total_activos", "N/D"),
        total_pasivos=datos.get("total_pasivos", "N/D"),
        total_deudas=datos.get("total_deudas", "N/D"),
        total_prestamos=datos.get("total_prestamos", "N/D"),
    )