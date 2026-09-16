# Servidor del chat SAMI contra el proyecto REAL de SAMECO (agente-biblioteca).
#   - Sirve index_sameco.html (un solo panel: el chat del Bibliotecario)
#   - Expone POST /api/chat replicando al agente "SAMI" de su Agent Studio:
#     mismas instrucciones, mismo modelo y mismo datastore (almacen_global).
#
# AUTENTICACIÓN: no hay token en el código — usa ADC (Application Default
# Credentials). La cuenta logueada con `gcloud auth application-default login`
# debe tener permisos IAM en el proyecto agente-biblioteca (Vertex AI User +
# Discovery Engine User): o te agregan el gmail, o logueás ADC con la cuenta
# SAMECO (eso pisa tu ADC del sandbox hasta volver a loguear la tuya).
#
# Requisitos: pip3 install --user google-genai requests
# Uso: python3 servidor_sameco.py            →  http://localhost:8501
#      python3 servidor_sameco.py --remoto   →  contra su Agent Runtime (si lo
#                                               deployan; completar AGENT_ENGINE)

import json
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from google import genai
from google.genai import types

PROJECT = "agente-biblioteca"
LOCATION = "global"   # los modelos gemini-3.x solo se sirven desde global
DATASTORE = ("projects/agente-biblioteca/locations/us/collections/"
             "default_collection/dataStores/almacen-global_1788552974869")
MODELO = "gemini-3.5-flash"   # el mismo que usa SAMI en su Agent Studio
# 8501 local (8500 queda para la demo del sandbox); en Cloud Run el puerto
# lo dicta la plataforma vía la variable PORT.
PUERTO = int(os.environ.get("PORT", 8501))

# Si SAMECO deploya a SAMI en Agent Runtime, pegar acá el nombre completo de
# la instancia (Implementaciones → Nombre del recurso) o pasarlo por env.
AGENT_ENGINE = os.environ.get(
    "AGENT_ENGINE",
    "projects/agente-biblioteca/locations/us-west1/reasoningEngines/8062630805551185920")

REMOTO = any(a in sys.argv for a in ("--remoto", "--remote"))

# Instrucciones tomadas del Get code del agente SAMI (Agent Studio de SAMECO)
INSTRUCCIONES = """Sos SAMI, el asistente para el evento de SAMECO: el asistente oficial sobre el Encuentro SAMECO 2026.

REGLAS:

1. CUÁNDO BUSCAR: Antes de responder cualquier pregunta, buscá SIEMPRE en la
   base de conocimiento (herramienta de datastore). Nunca respondas desde tu
   conocimiento general ni de memoria, aunque creas saber la respuesta.

2. CÓMO RESPONDER: Basá cada afirmación solo en lo que devolvió la búsqueda.
   Al final de cada respuesta indicá la fuente con el formato:
   (Fuente: [nombre del documento]).
   Si usaste varios documentos, citá cada uno.

3. SI NO ESTÁ: Si la búsqueda no devuelve la información, respondé exactamente:
   "No cuento con esa información en los documentos de SAMECO. Te sugiero
   escribir a la organización." No inventes datos, nombres, fechas ni cifras.

4. PREGUNTAS AMBIGUAS: Si la pregunta es ambigua (por ejemplo "¿y los costos?"),
   hacé UNA repregunta breve para aclarar, o respondé lo más relevante indicando
   qué interpretaste.

TONO: Español rioplatense, cordial y profesional. Respuestas breves: 3 a 5
oraciones, o una lista corta si enumera varios trabajos. Al recomendar trabajos
del archivo, mencioná título, año y autores si constan.

LÍMITES: Solo temas relacionados los documentos provistos . Ante cualquier
otro tema, decliná amablemente y ofrecé ayudar con el archivo o el encuentro.

Cuando cites un documento, incluí también su enlace de descarga: tomá la URI
de los metadatos que referencian al documento si es que es posible."""

# ----- Modo local: réplica con google-genai + grounding en el datastore -----
client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
TOOL = types.Tool(retrieval=types.Retrieval(
    vertex_ai_search=types.VertexAISearch(datastore=DATASTORE)))


def responder_local(mensajes):
    contents = [
        types.Content(role=("user" if m["rol"] == "user" else "model"),
                      parts=[types.Part.from_text(text=m["texto"])])
        for m in mensajes
    ]
    resp = client.models.generate_content(
        model=MODELO,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCIONES, tools=[TOOL]),
    )
    fuentes = []
    try:
        for ch in resp.candidates[0].grounding_metadata.grounding_chunks:
            rc = ch.retrieved_context
            if rc and rc.title and rc.title not in fuentes:
                fuentes.append(rc.title)
    except (AttributeError, TypeError, IndexError):
        pass
    return resp.text or "(sin respuesta)", fuentes


# ----- Modo remoto: SAMI deployado en Agent Runtime de SAMECO -----
# Va por la API REST de la instancia (los endpoints :query / :streamQuery que
# muestra la consola en Implementaciones), sin depender del SDK de aiplatform
# (cuya interfaz de agent_engines cambia entre versiones).
sesiones = {}   # una sesión server-side POR VISITANTE (id que genera la página)

if REMOTO:
    import google.auth
    import google.auth.transport.requests
    import requests as _rq
    _region = AGENT_ENGINE.split("/")[3]
    _BASE = f"https://{_region}-aiplatform.googleapis.com/v1/{AGENT_ENGINE}"
    # Las sesiones se crean con la API administrada de Sessions (no es un
    # class_method del agente): POST .../reasoningEngines/ID/sessions
    _SESIONES = f"https://{_region}-aiplatform.googleapis.com/v1beta1/{AGENT_ENGINE}/sessions"
    _creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"])

    def _auth():
        if not _creds.valid:
            _creds.refresh(google.auth.transport.requests.Request())
        return {"Authorization": f"Bearer {_creds.token}"}


def responder_remoto(mensajes, cliente):
    if cliente not in sesiones:
        try:
            r = _rq.post(_SESIONES, headers=_auth(), timeout=60,
                         json={"userId": cliente})
            r.raise_for_status()
            j = r.json()
            nombre = (j.get("response") or {}).get("name") or j.get("name", "")
            sesiones[cliente] = nombre.split("/sessions/")[1].split("/")[0]
        except Exception:
            sesiones[cliente] = None   # sin sesión: cada turno va suelto
    entrada = {"user_id": cliente, "message": mensajes[-1]["texto"]}
    if sesiones[cliente]:
        # Solo el último mensaje: el contexto lo mantiene la sesión en Google
        entrada["session_id"] = sesiones[cliente]
    r = _rq.post(_BASE + ":streamQuery", headers=_auth(), timeout=120,
                 json={"class_method": "stream_query", "input": entrada})
    r.raise_for_status()
    partes, fuentes = [], []
    for linea in r.text.splitlines():
        try:
            ev = json.loads(linea)
        except ValueError:
            continue
        for p in (ev.get("content") or {}).get("parts", []):
            if p.get("text") and not p.get("thought"):
                partes.append(p["text"])
        for ch in (ev.get("grounding_metadata") or {}).get("grounding_chunks", []):
            titulo = (ch.get("retrieved_context") or {}).get("title")
            if titulo and titulo not in fuentes:
                fuentes.append(titulo)
    return "".join(partes) or "(sin respuesta)", fuentes


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/index_sameco.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        datos = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        try:
            if REMOTO:
                cliente = str(datos.get("cliente", "anonimo"))[:64]
                texto, fuentes = responder_remoto(datos["mensajes"], cliente)
            else:
                texto, fuentes = responder_local(datos["mensajes"])
            cuerpo = {"texto": texto, "fuentes": fuentes}
        except Exception as e:  # errores de auth/API legibles en el panel
            cuerpo = {"texto": f"[Error del servidor: {e}]", "fuentes": []}
        raw = json.dumps(cuerpo, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if REMOTO and "COMPLETAR_TRAS_DEPLOY" in AGENT_ENGINE:
        print("Falta el ID de la instancia: completá AGENT_ENGINE en este archivo")
        print("(o export AGENT_ENGINE=...) con el nombre que muestra Agent Runtime.")
        sys.exit(1)
    modo = "REMOTO (Agent Runtime)" if REMOTO else "local (réplica con google-genai)"
    print(f"Chat SAMI (proyecto {PROJECT}) en http://localhost:{PUERTO}  ·  modo {modo}")
    ThreadingHTTPServer(("", PUERTO), Handler).serve_forever()
