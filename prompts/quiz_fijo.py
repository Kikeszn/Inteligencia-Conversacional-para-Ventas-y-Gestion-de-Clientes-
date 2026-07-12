"""
Quiz fijo de 3 preguntas para el Tutor IA.

Definido en codigo (no generado dinamicamente por el LLM) para cumplir
el criterio de aceptacion de la Historia 2. Si manana quieren usar el
Tutor con otro concepto, agreguen otra entrada a QUIZ_POR_CONCEPTO.
"""

QUIZ_POR_CONCEPTO = {
    "interes compuesto": [
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
    ],
}


def obtener_quiz(concepto: str) -> list[dict]:
    """Devuelve el quiz fijo para un concepto. Si no existe, devuelve una
    lista vacia (la app debe manejar ese caso, aunque para el demo solo
    se usa 'interes compuesto')."""
    return QUIZ_POR_CONCEPTO.get(concepto, [])


def calificar_quiz(concepto: str, respuestas: list[int]) -> dict:
    """Compara las respuestas del usuario (indices elegidos) contra las
    correctas y devuelve un resumen en texto listo para guardar en
    `resultado_quiz`, mas el puntaje crudo por si se necesita luego."""
    preguntas = obtener_quiz(concepto)
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
