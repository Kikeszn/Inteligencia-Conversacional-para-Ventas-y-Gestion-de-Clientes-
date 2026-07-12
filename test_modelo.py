"""
Script temporal y desechable para confirmar si el modelo configurado en
llm_client.py (mismo cliente, misma API key, mismo _MODEL_NAME) responde.
Se corre una sola vez desde la terminal: python test_modelo.py
No se integra a app.py -- borrar despues de usarlo.
"""

import traceback

from llm_client import _MODEL_NAME, _client

print(f"Modelo configurado: {_MODEL_NAME}")

try:
    respuesta = _client.models.generate_content(
        model=_MODEL_NAME,
        contents="Responde solo con la palabra: funciona",
    )
    print("\n--- Respuesta completa (objeto) ---")
    print(respuesta)
    print("\n--- Texto de la respuesta ---")
    print(respuesta.text)
except Exception:
    print("\n--- ERROR al llamar al modelo ---")
    traceback.print_exc()
