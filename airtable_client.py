import os
from dotenv import load_dotenv
from pyairtable import Api

load_dotenv()

_api = Api(os.getenv("AIRTABLE_TOKEN"))
_table = _api.table(
    os.getenv("AIRTABLE_BASE_ID"),
    os.getenv("AIRTABLE_TABLE_NAME")
)


def crear_lead(nombre_usuario: str) -> str:
    """Crea un lead nuevo al iniciar la conversacion con el Tutor.
    Retorna el record_id de Airtable para actualizarlo despues."""
    registro = _table.create({
        "nombre_usuario": nombre_usuario,
        "estado_tecnico": "En Tutoria",
    })
    return registro["id"]


def actualizar_lead(record_id: str, campos: dict) -> None:
    """Actualiza un subconjunto de campos de un lead existente."""
    _table.update(record_id, campos)


def leer_leads_pendientes() -> list[dict]:
    """Retorna los leads que esperan aprobacion del ejecutivo."""
    return _table.all(
        formula="{estado_tecnico} = 'Esperando Aprobacion'"
    )