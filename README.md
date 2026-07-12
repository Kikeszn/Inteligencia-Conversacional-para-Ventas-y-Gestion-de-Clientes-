# Asistente Future Academy

Sistema de dos agentes de IA (Tutor educativo + Comercial) que conversan con el usuario en una sola interfaz de chat, sin que este tenga que elegir con cuál está hablando. Un agente enrutador clasifica cada mensaje en segundo plano y deriva la conversación al agente correspondiente, mientras el contexto comercial y educativo se registra automáticamente en un CRM (Airtable).

**Hackathon de Agentes Financieros IA — Track 1: Inteligencia Conversacional para Ventas y Gestión de Clientes (CRM)**

---

## Índice

- [El problema que resuelve](#el-problema-que-resuelve)
- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Variables de entorno](#variables-de-entorno)
- [Campos requeridos en Airtable](#campos-requeridos-en-airtable)
- [Cómo correr el proyecto](#cómo-correr-el-proyecto)
- [Despliegue](#despliegue)
- [Flujo funcional](#flujo-funcional)
- [Tabla de pruebas](#tabla-de-pruebas)
- [Uso de la API de Gemini](#uso-de-la-api-de-gemini)
- [Alcance y limitaciones](#alcance-y-limitaciones)

---

## El problema que resuelve

Capta, califica y nutre prospectos financieros mientras registra el contexto comercial y educativo en un CRM, sin que el usuario tenga que navegar menús ni indicar explícitamente qué tipo de ayuda busca.

- **Historia 1 — Calificación conversacional de leads:** el Agente Comercial identifica si el prospecto es B2B o B2C, calcula una prioridad simple y registra el contacto en el CRM.
- **Historia 2 — Tutor financiero:** el Tutor IA explica conceptos financieros citando la fuente, propone un quiz corto, y registra el tema de interés con consentimiento explícito del usuario.
- **Historia 3 — Seguimiento y derivación comercial:** el sistema resume necesidad, objeciones y etapa del embudo, sugiere una acción, y deja la aprobación final en manos de un ejecutivo humano.

## Arquitectura

```
                    ┌─────────────────────-┐
   Usuario  ──────► │   Interfaz de chat   │
                    │       (app.py)       │
                    └──────────┬───────────┘
                               │ cada mensaje nuevo
                               ▼
                    ┌───────────────────-──┐
                    │  Agente Enrutador    │  clasifica sin conversar
                    │  (router_prompt.py)  │  → "tutor" | "comercial"
                    └──────────┬───────────┘
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
      ┌────────────────────-─┐     ┌─────────────────────--─┐
      │     Tutor IA         │     │   Agente Comercial     │
      │  (tutor_prompt.py)   │     │ (comercial_prompt.py)  │
      │  - explica conceptos │     │  - identifica B2B/B2C  │
      │  - cita la fuente    │     │  - perfila en 3 turnos │
      │  - genera quiz       │     │  - pide datos negocio  │
      │  - gate consentim.   │     │  - resume y prioriza   │
      └──────────┬───────────┘     └───────────┬────────────┘
                 └─────────────┬───────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Cliente de Airtable  │  crear_lead / actualizar_lead
                    │ (airtable_client.py)  │  leer_leads_pendientes
                    └─────────────────────┘
```

La lógica está separada en tres capas independientes:

| Capa | Archivo(s) | Responsabilidad |
|---|---|---|
| Interfaz | `app.py` | Renderiza el chat en Streamlit y orquesta la máquina de estados. No conoce Airtable ni Gemini directamente. |
| Agentes | `prompts/*.py` | Los system prompts y reglas de negocio de cada agente (Enrutador, Tutor, Comercial). |
| Modelo de lenguaje | `llm_client.py` | Único punto de contacto con la API de Gemini. |
| CRM | `airtable_client.py` | Único punto de contacto con Airtable. |
| Estilos | `styles.py` + `static/style.css` | CSS separado del código Python. |

## Estructura del proyecto

```
proyecto/
├── app.py                     # Interfaz Streamlit + orquestación del flujo
├── llm_client.py               # Cliente de la API de Gemini (google-genai)
├── airtable_client.py          # Cliente del CRM (pyairtable)
├── styles.py                   # Inyecta el CSS personalizado en Streamlit
├── prompts/
│   ├── router_prompt.py         # Agente Enrutador
│   ├── tutor_prompt.py          # Agente Tutor + generador de quiz dinámico
│   ├── comercial_prompt.py      # Agente Comercial + contexto de datos del negocio
│   └── quiz.py                  # Quiz de respaldo + calificación de respuestas
├── static/
│   ├── style.css                 # Estilos (paleta, tipografía, componentes)
│   └── images/logo.png           # Logo del proyecto
├── requirements.txt
├── startup.sh                  # Arranque para despliegue (Cloudflare Tunnel)
├── .env.example                 # Plantilla de variables de entorno
└── .gitignore
```

## Requisitos previos

- Python 3.11 o superior
- Una base de Airtable con la tabla `Leads` ya creada (ver [campos requeridos](#campos-requeridos-en-airtable))
- Una API key de Gemini ([aistudio.google.com/apikey](https://aistudio.google.com/apikey))

## Instalación

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd <carpeta-del-proyecto>

# Crear y activar un entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Variables de entorno

Crea un archivo `.env` en la raíz del proyecto (usa `.env.example` como plantilla):

```env
GEMINI_API_KEY=
AIRTABLE_TOKEN=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=Leads
```

| Variable | Dónde obtenerla |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) → *Create API key* |
| `AIRTABLE_TOKEN` | [airtable.com/create/tokens](https://airtable.com/create/tokens), con permisos `data.records:read` y `data.records:write` sobre tu base |
| `AIRTABLE_BASE_ID` | Se ve en la URL de tu base (`airtable.com/appXXXXXXXXXXXXXX/...`) |
| `AIRTABLE_TABLE_NAME` | El nombre exacto de tu tabla, por defecto `Leads` |

**El archivo `.env` nunca se sube al repositorio** (ya está en `.gitignore`).

## Campos requeridos en Airtable

La tabla `Leads` debe tener estos campos creados de antemano (el token de la API no tiene permiso para crear opciones nuevas de campos tipo selección sobre la marcha):

| Campo | Tipo |
|---|---|
| `nombre_usuario` | Texto |
| `estado_tecnico` | Selección única: `En Tutoria`, `Transferido`, `Esperando Aprobacion`, `Aprobado` |
| `tema_interes_inicial` | Texto |
| `resultado_quiz` | Texto |
| `fuente_contenido` | Texto |
| `consentimiento` | Casilla (checkbox) |
| `fecha_consent` | Fecha |
| `tipo_prospecto` | Texto o selección: `B2B`, `B2C` |
| `resumen_necesidad` | Texto largo |
| `objeciones` | Texto largo |
| `etapa_embudo` | Selección: `Descubrimiento`, `Consideracion`, `Decision` |
| `prioridad` | Selección: `Alta`, `Media`, `Baja` |
| `justificacion_score` | Texto largo |
| `accion_sugerida` | Selección: `Agendar reunion`, `Enviar material educativo`, `Derivar a especialista` |
| `datos_negocio_compartidos` | Casilla (checkbox) |
| `ingresos_dia` | Número |
| `ingresos_mes` | Número |
| `total_activos` | Número |
| `total_pasivos` | Número |
| `total_deudas` | Número |
| `total_prestamos` | Número |

## Cómo correr el proyecto

```bash
streamlit run app.py
```

La app abre automáticamente en `http://localhost:8501`.

## Despliegue

**Opción A — Streamlit Community Cloud** (recomendada): conectar el repositorio en [share.streamlit.io](https://share.streamlit.io), configurar `app.py` como archivo principal, y pegar las mismas variables de entorno en *Settings → Secrets*.

**Opción B — Cloudflare Tunnel** (para exponer una instancia corriendo localmente): el proyecto incluye `startup.sh`, que levanta la app en el puerto 8000 lista para ser expuesta por `cloudflared`.

## Flujo funcional

1. El usuario escribe su nombre y comienza el chat. Se crea un lead en Airtable con `estado_tecnico = En Tutoria`.
2. Cada mensaje que escribe pasa primero por el **Agente Enrutador**, que decide si lo atiende el Tutor o el Comercial — el usuario nunca elige esto explícitamente.
3. **Si es el Tutor:** responde citando la fuente y evitando inventar cifras reales (regla de antialucinación). El usuario puede pedir un quiz de 3 preguntas generado a partir de lo conversado; al responderlo se le pide consentimiento explícito antes de registrar su interés como señal comercial.
4. **Si es el Comercial:** en su primer mensaje pregunta explícitamente si el prospecto es B2B o B2C, ofrece la opción de compartir datos financieros del negocio (formulario opcional), y perfila al prospecto en un máximo de 3 intercambios.
5. Al cerrar la conversación comercial, se genera un resumen estructurado (necesidad, objeciones, etapa del embudo, prioridad, acción sugerida) y el lead queda con `estado_tecnico = Esperando Aprobacion`, a la espera de que un ejecutivo humano apruebe la siguiente acción.

## Tabla de pruebas

| Input | Esperado | Obtenido |
|---|---|---|
| "Quiero aprender sobre el interés compuesto" | El Enrutador deriva al Tutor | |
| "Necesito un asesor para mi empresa" | El Enrutador deriva al Comercial | |
| Responder el quiz del Tutor y aceptar el consentimiento | `consentimiento = True`, `estado_tecnico = Transferido` en Airtable | |
| Completar 3 turnos con el Comercial | Se genera el resumen JSON y `estado_tecnico = Esperando Aprobacion` | |
| Llenar el formulario de datos del negocio | `datos_negocio_compartidos = True` + campos financieros guardados | |

*(Completar la columna "Obtenido" con capturas o resultados reales antes de la entrega.)*

## Uso de la API de Gemini

Este proyecto usa la **API de Gemini de Google** (`google-genai`, modelo `gemini-3.1-flash-lite`) para los tres agentes: clasificación de intención, generación de respuestas conversacionales del Tutor y el Comercial, generación dinámica del quiz, y extracción de resúmenes estructurados en JSON.

## Alcance y limitaciones

- El flujo B2B del Comercial usa el mismo agente que el B2C; el campo `tipo_prospecto` ya está en el modelo de datos y se completa automáticamente al identificar la intención.
- Si el usuario no da su consentimiento en el Tutor, el sistema no guarda ninguna señal comercial y respeta esa decisión.
- Las acciones sugeridas por el Comercial (agendar reunión, enviar material, derivar a especialista) quedan como propuesta: un ejecutivo humano debe aprobarlas antes de ejecutarse.

