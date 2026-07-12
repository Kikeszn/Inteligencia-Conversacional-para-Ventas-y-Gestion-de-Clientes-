"""
Calificacion del quiz del Tutor IA.

El quiz de 3 preguntas ya NO esta fijo en codigo: lo genera el propio
agente Tutor en base al historial de la conversacion (ver
generar_quiz_tutor en llm_client.py, que usa QUIZ_GENERATOR_PROMPT /
construir_prompt_quiz de prompts/tutor_prompt.py). Este modulo solo se
encarga de:
1. Servir de quiz de respaldo si la generacion con el modelo falla.
2. Calificar las respuestas del usuario contra la clave de respuestas
   que vino en el quiz generado.
"""

QUIZ_FALLBACK = [
    {
        "pregunta": "¿Que diferencia al interes compuesto del interes simple?",
        "opciones": [
            "El interes compuesto se calcula solo sobre el monto inicial",
            "El interes compuesto se calcula sobre el monto inicial mas los intereses acumulados",
            "El interes compuesto no depende del tiempo",
        ],
        "correcta": 1,
    },
    {
        "pregunta": "¿Que variable tiene mas impacto en el crecimiento del interes compuesto a largo plazo?",
        "opciones": [
            "El color de la cuenta bancaria",
            "El tiempo que el dinero permanece invertido",
            "El numero de veces que revisas tu saldo",
        ],
        "correcta": 1,
    },
    {
        "pregunta": "Si dejas tu dinero invertido mas anos sin retirarlo, en general el efecto del interes compuesto es:",
        "opciones": [
            "Menor, porque el dinero 'se cansa'",
            "Igual siempre, no importa el tiempo",
            "Mayor, porque los intereses generan mas intereses",
        ],
        "correcta": 2,
    },
]


def calificar_quiz(preguntas: list[dict], respuestas: list[int]) -> dict:
    """Compara las respuestas del usuario (indices elegidos) contra las
    correctas del quiz recibido (generado por el Tutor) y devuelve un
    resumen en texto listo para guardar en `resultado_quiz`, mas el
    puntaje crudo por si se necesita luego."""
    correctas = 0
    detalle = []
    for i, pregunta in enumerate(preguntas):
        elegida = respuestas[i] if i < len(respuestas) else None
        acierto = elegida == pregunta["correcta"]
        if acierto:
            correctas += 1
        detalle.append(f"P{i + 1}: {'correcta' if acierto else 'incorrecta'}")

    resumen_texto = f"{correctas}/{len(preguntas)} correctas — " + ", ".join(detalle)
    return {"correctas": correctas, "total": len(preguntas), "resumen_texto": resumen_texto}