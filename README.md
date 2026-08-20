# Asistente Q&A SAMECO — materiales y scripts

Materiales del curso (4 sesiones) y scripts de apoyo para el asistente de
preguntas y respuestas de SAMECO sobre Google Cloud (Agent Search / AI
Applications): 1 agente + 2 bibliotecas de documentos ("Evento octubre 2026"
y "Archivo histórico").

- `curso/instructivos/` — los instructivos paso a paso (empezar por `00_Conceptos_basicos.md`)
- `curso/slides/` — las presentaciones de las 4 sesiones
- `curso/material_practica/` — documentos ficticios para practicar en un entorno de prueba
- `curso/scripts/` — scripts de QA automático, fichas de metadatos y videos de YouTube
- `curso/widget/` — página de demo comparativa (widget oficial + agente propio)

Los instructivos y las slides se leen sin instalar nada. Lo que sigue hace
falta **solo para correr los scripts**.

## 1. Instalar Python (una sola vez por computadora)

Hace falta **Python 3.10 o más nuevo**.

- **Windows**: bajar el instalador de <https://www.python.org/downloads/> y,
  muy importante, tildar **"Add python.exe to PATH"** en la primera pantalla.
- **Mac**: viene con Python, pero conviene el actualizado: instalar
  [Homebrew](https://brew.sh) y después `brew install python`.

Verificar en una terminal: `python3 --version` (en Windows: `py --version`).

## 2. Instalar Google Cloud SDK (una sola vez)

Es la herramienta `gcloud`, que maneja la identidad ante Google.

- **Windows**: instalador en <https://cloud.google.com/sdk/docs/install>
- **Mac**: `brew install --cask google-cloud-sdk`

## 3. Crear el entorno virtual del proyecto (una sola vez)

Un *venv* es una carpeta con las dependencias aisladas de este proyecto: no
toca nada del resto de la computadora. Desde la carpeta del repo:

```bash
# Mac / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Cada vez que se abra una terminal nueva para usar los scripts, repetir solo
la línea del `activate` (se nota porque el prompt pasa a decir `(.venv)`).

## 4. Autenticarse con Google (una vez por computadora)

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project TU_PROJECT_ID
```

Se abre el navegador: entrar con la cuenta que tiene acceso al proyecto y
**tildar todas las casillas de permisos** antes de aceptar (si falta la de
Google Cloud, la autenticación falla con un error de "scope"). Esto guarda
una credencial local (ADC) que los scripts usan solos; se revoca cuando se
quiera con `gcloud auth application-default revoke`.

Además, el proyecto de Google Cloud debe tener habilitadas las APIs
**Vertex AI** y **Discovery Engine** (la consola las ofrece habilitar al
primer uso).

## 5. Configurar y correr

Cada script tiene su configuración al principio del archivo (`PROJECT_ID`,
`BUCKET`, `ENGINE`…): ajustarla al proyecto propio antes de correrlo. Qué hace
cada uno:

| Script | Para qué sirve |
|---|---|
| `curso/scripts/correr_set_pruebas.py` | Corre el set de preguntas de prueba contra el asistente y califica las respuestas (juez automático) → CSV |
| `curso/scripts/generar_fichas.py` | Genera las fichas de metadatos de los documentos del bucket con Gemini (ver instructivo D) |
| `curso/scripts/generar_transcripciones.py` | Convierte videos de YouTube (`videos.txt`) en documentos indexables |
| `curso/widget/servidor_demo.py` | Demo comparativa en `http://localhost:8500`; con `--remoto` usa el agente publicado en Agent Runtime |
| `curso/slides/generar_pptx.py` | Regenera los 4 PPT del curso (editar este script, no los .pptx) |

Ejemplo, con el venv activado:

```bash
python3 curso/scripts/correr_set_pruebas.py
```

**Costos**: todos estos scripts usan Gemini Flash y cuestan centavos por
corrida (verificado ago-2026). En cuentas de prueba gratuita la cuota es de
~5 llamadas por minuto; los scripts ya esperan y reintentan solos.
