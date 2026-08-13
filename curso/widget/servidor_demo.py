# Servidor de la página de demo comparativa (Sesión "las 2 cosas"):
#   - Sirve index.html (widget oficial de la app de búsqueda + panel Bibliotecario)
#   - Expone POST /api/chat: replica al agente "Bibliotecario SAMECO" de Agent
#     Studio llamando a Gemini con grounding sobre la app (sus 2 datastores).
#
# Esto ES el "desarrollo propio" que exige el camino Agent Platform (no existe
# widget embebible para esos agentes); la app de búsqueda, en cambio, trae el
# widget hecho. Ese contraste es el punto didáctico de la página.
#
# Requisitos: pip3 install --user google-genai ; gcloud auth application-default login
# Uso: python3 servidor_demo.py  →  http://localhost:8500

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

from google import genai
from google.genai import types

PROJECT = "sameco-conf-2026"
LOCATION = "global"  # endpoint del modelo; si da error de ubicación probar "us-central1"
ENGINE = ("projects/sameco-conf-2026/locations/us/collections/default_collection/"
          "engines/asistente-sameco-pr-ctica_1786499519728")
MODELO = "gemini-2.5-flash"
PUERTO = 8500

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

client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
TOOL = types.Tool(retrieval=types.Retrieval(
    vertex_ai_search=types.VertexAISearch(engine=ENGINE)))


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        datos = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        contents = [
            types.Content(role=("user" if m["rol"] == "user" else "model"),
                          parts=[types.Part.from_text(text=m["texto"])])
            for m in datos["mensajes"]
        ]
        try:
            resp = client.models.generate_content(
                model=MODELO,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=INSTRUCCIONES, tools=[TOOL]),
            )
            texto = resp.text or "(sin respuesta)"
            fuentes = []
            try:
                for ch in resp.candidates[0].grounding_metadata.grounding_chunks:
                    rc = ch.retrieved_context
                    if rc and rc.title and rc.title not in fuentes:
                        fuentes.append(rc.title)
            except (AttributeError, TypeError, IndexError):
                pass
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
    print(f"Demo comparativa en http://localhost:{PUERTO}")
    HTTPServer(("", PUERTO), Handler).serve_forever()
