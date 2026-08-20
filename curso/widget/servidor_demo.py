# Servidor de la página de demo comparativa (Sesión "las 2 cosas"):
#   - Sirve index.html (widget oficial de la app de búsqueda + panel Bibliotecario)
#   - Expone POST /api/chat con DOS modos:
#       modo local (default): replica al "Bibliotecario SAMECO" llamando a Gemini
#         con grounding sobre la app (sus 2 datastores). Sin nada deployado.
#       modo remoto (--remoto): le habla al agente REAL deployado en Agent
#         Runtime (el botón Deploy de Agent Studio). Requiere la instancia viva
#         (factura por hora) y completar AGENT_ENGINE con su ID.
#
# El contraste didáctico: en modo local el contexto lo mantiene ESTE servidor
# (manda el historial completo en cada llamada); en modo remoto la sesión vive
# en Google (Sessions de Agent Runtime) y solo se manda el último mensaje.
#
# Requisitos: pip3 install --user google-genai ; gcloud auth application-default login
#   modo remoto además: pip3 install --user "google-cloud-aiplatform[agent_engines]"
# Uso: python3 servidor_demo.py            →  http://localhost:8500 (modo local)
#      python3 servidor_demo.py --remoto   →  ídem, contra el agente hosteado

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

from google import genai
from google.genai import types

PROJECT = "sameco-conf-2026"
LOCATION = "global"  # endpoint del modelo; si da error de ubicación probar "us-central1"
ENGINE = ("projects/sameco-conf-2026/locations/us/collections/default_collection/"
          "engines/asistente-sameco-pr-ctica_1786499519728")
MODELO = "gemini-2.5-flash"
PUERTO = 8500

# Modo remoto: el nombre completo de la instancia de Agent Runtime.
# Se obtiene tras el Deploy en: console.cloud.google.com/agent-platform/runtimes
# (o por env: export AGENT_ENGINE="projects/.../reasoningEngines/123...")
AGENT_ENGINE = os.environ.get(
    "AGENT_ENGINE",
    "projects/sameco-conf-2026/locations/us-west1/reasoningEngines/1435689506991767552")

REMOTO = "--remoto" in sys.argv

INSTRUCCIONES = """Sos el Bibliotecario de SAMECO: el asistente oficial sobre el archivo histórico
de trabajos de mejora continua y el Encuentro SAMECO 2026.

REGLAS:
1. CUÁNDO BUSCAR: Antes de responder cualquier pregunta, buscá SIEMPRE en la
   base de conocimiento. Nunca respondas desde tu conocimiento general.
2. CÓMO RESPONDER: Basá cada afirmación solo en lo que devolvió la búsqueda.
   Al final indicá la fuente: (Fuente: [nombre del documento]).
3. SI NO ESTÁ: Respondé exactamente: "No cuento con esa información en los
   documentos de SAMECO. Te sugiero escribir a la organización." No inventes.
4. AMBIGUAS: Ante una pregunta ambigua, hacé UNA repregunta breve para aclarar.

TONO: Español rioplatense, cordial y profesional. 3 a 5 oraciones.
LÍMITES: Solo temas de SAMECO. Ante otros temas, decliná amablemente."""

# ----- Modo local: réplica con google-genai + grounding -----
client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
TOOL = types.Tool(retrieval=types.Retrieval(
    vertex_ai_search=types.VertexAISearch(engine=ENGINE)))


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


# ----- Modo remoto: el agente deployado en Agent Runtime -----
motor = None
sesion_remota = {"id": None}   # una sesión server-side por corrida del servidor

if REMOTO:
    import vertexai
    from vertexai import agent_engines
    region = AGENT_ENGINE.split("/")[3]
    vertexai.init(project=PROJECT, location=region)
    motor = agent_engines.get(AGENT_ENGINE)


def responder_remoto(mensajes):
    if sesion_remota["id"] is None:
        s = motor.create_session(user_id="demo-comparativa")
        sesion_remota["id"] = s["id"] if isinstance(s, dict) else s.id
    partes, fuentes = [], []
    # Solo el último mensaje: el contexto lo mantiene la sesión en Google
    for ev in motor.stream_query(user_id="demo-comparativa",
                                 session_id=sesion_remota["id"],
                                 message=mensajes[-1]["texto"]):
        contenido = (ev.get("content") or {}) if isinstance(ev, dict) else {}
        for p in contenido.get("parts", []):
            if p.get("text") and not p.get("thought"):
                partes.append(p["text"])
        gm = ev.get("grounding_metadata") if isinstance(ev, dict) else None
        for ch in (gm or {}).get("grounding_chunks", []):
            titulo = (ch.get("retrieved_context") or {}).get("title")
            if titulo and titulo not in fuentes:
                fuentes.append(titulo)
    return "".join(partes) or "(sin respuesta)", fuentes


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        datos = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        try:
            if REMOTO:
                texto, fuentes = responder_remoto(datos["mensajes"])
            else:
                texto, fuentes = responder_local(datos["mensajes"])
            cuerpo = {"texto": texto, "fuentes": fuentes}
        except Exception as e:  # errores de auth/API legibles en el panel
            cuerpo = {"texto": f"[Error del servidor demo: {e}]", "fuentes": []}
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
    print(f"Demo comparativa en http://localhost:{PUERTO}  ·  modo {modo}")
    HTTPServer(("", PUERTO), Handler).serve_forever()
