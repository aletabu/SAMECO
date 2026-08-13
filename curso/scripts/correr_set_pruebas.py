# Corre el set de pruebas contra la app de búsqueda (Answer API de Discovery
# Engine) y hace triage automático de cada respuesta con Gemini como juez.
#
# Qué hace por cada pregunta de set_pruebas.json:
#   1. Llama a la Answer API del engine (misma app del widget), con sesión
#      encadenada para las preguntas de seguimiento.
#   2. Le pide a Gemini un veredicto contra la respuesta esperada:
#      correcta / incompleta / inventada / fallback_correcto / fallback_incorrecto
#   3. Escribe resultados.csv (para la planilla de calidad) y un resumen en pantalla.
#
# El juez automático es TRIAGE, no sentencia: las 'correcta' y los fallbacks de
# canarias son confiables; las 'incompleta' e 'inventada' se revisan a mano.
#
# Requisitos: pip3 install --user google-genai requests
#             gcloud auth application-default login  (con quota project seteado)
# Uso:        python3 correr_set_pruebas.py

import csv
import json
import os
import sys
from datetime import date

import google.auth
import google.auth.transport.requests
import requests
from google import genai
from google.genai import types

PROJECT = "sameco-conf-2026"
LOCATION = "us"                       # ubicación del engine (multi-región)
ENGINE = "asistente-sameco-pr-ctica_1786499519728"
MODELO_JUEZ = "gemini-2.5-flash"
PREAMBLE = ("Sos el asistente oficial de SAMECO. Respondé solo con la información "
            "de los documentos. Si no está, decilo y sugerí escribir a la "
            "organización. Español, breve, citando la fuente.")

BASE = (f"https://{LOCATION}-discoveryengine.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{LOCATION}/collections/default_collection/engines/{ENGINE}")

VEREDICTOS = ["correcta", "incompleta", "inventada", "fallback_correcto", "fallback_incorrecto"]
ESQUEMA_JUEZ = {
    "type": "OBJECT",
    "properties": {
        "veredicto": {"type": "STRING", "enum": VEREDICTOS},
        "justificacion": {"type": "STRING", "description": "1-2 oraciones"},
    },
    "required": ["veredicto", "justificacion"],
}


def token():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def preguntar(tok, texto, sesion=None):
    """Llama a la Answer API. Devuelve (respuesta, fuentes, nombre_de_sesion)."""
    cuerpo = {
        "query": {"text": texto},
        "answerGenerationSpec": {
            "ignoreAdversarialQuery": True,
            "includeCitations": True,
            "promptSpec": {"preamble": PREAMBLE},
        },
        "session": sesion or f"projects/{PROJECT}/locations/{LOCATION}/collections/default_collection/engines/{ENGINE}/sessions/-",
    }
    r = requests.post(f"{BASE}/servingConfigs/default_search:answer",
                      headers={"Authorization": f"Bearer {tok}",
                               "Content-Type": "application/json"},
                      json=cuerpo, timeout=120)
    r.raise_for_status()
    data = r.json()
    answer = data.get("answer", {})
    texto_resp = answer.get("answerText", "(sin respuesta)")
    fuentes = []
    for ref in answer.get("references", []):
        doc = (ref.get("chunkInfo", {}).get("documentMetadata", {})
               or ref.get("unstructuredDocumentInfo", {}))
        titulo = doc.get("title") or doc.get("uri", "")
        if titulo and titulo not in fuentes:
            fuentes.append(titulo)
    nombre_sesion = data.get("session", {}).get("name")
    return texto_resp, fuentes, nombre_sesion


def juzgar(ia, pregunta, esperado, obtenido, tipo):
    prompt = f"""Evaluá la respuesta de un asistente Q&A con RAG.

PREGUNTA: {pregunta}
TIPO: {tipo} (si es 'canaria', la respuesta correcta es admitir que no tiene el dato)
RESPUESTA ESPERADA (referencia): {esperado}
RESPUESTA DEL ASISTENTE: {obtenido}

Veredictos: correcta (dice lo esperado; información ADICIONAL plausible del
documento NO la invalida), incompleta (le falta parte de lo esperado),
inventada (afirma algo que CONTRADICE lo esperado o es claramente falso),
fallback_correcto (canaria que admite no saber), fallback_incorrecto (dijo
'no sé' ante una pregunta que SÍ tenía respuesta)."""
    r = ia.models.generate_content(
        model=MODELO_JUEZ, contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=ESQUEMA_JUEZ))
    return json.loads(r.text)


def main():
    aca = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(aca, "set_pruebas.json"), encoding="utf-8") as f:
        preguntas = json.load(f)["preguntas"]

    tok = token()
    ia = genai.Client(vertexai=True, project=PROJECT, location="global")
    sesiones = {}   # n -> nombre de sesión (para encadenar seguimientos)
    filas = []

    for p in preguntas:
        sesion_previa = sesiones.get(p.get("sigue_a"))
        try:
            resp, fuentes, ses = preguntar(tok, p["pregunta"], sesion_previa)
        except requests.HTTPError as e:
            print(f"#{p['n']:>2} ERROR API: {e.response.status_code} {e.response.text[:200]}")
            continue
        sesiones[p["n"]] = ses
        try:
            j = juzgar(ia, p["pregunta"], p["esperado"], resp, p["tipo"])
        except Exception as e:
            j = {"veredicto": "sin_juez", "justificacion": str(e)[:120]}
        marca = {"correcta": "✅", "fallback_correcto": "✅🐤",
                 "incompleta": "🟡", "inventada": "🔴",
                 "fallback_incorrecto": "🔴"}.get(j["veredicto"], "❔")
        print(f"#{p['n']:>2} [{p['bloque']}/{p['tipo']:<11}] {marca} {j['veredicto']:<19} {p['pregunta'][:55]}")
        filas.append({
            "n": p["n"], "bloque": p["bloque"], "tipo": p["tipo"],
            "pregunta": p["pregunta"], "esperado": p["esperado"],
            "respuesta": resp, "fuentes": " | ".join(fuentes),
            "veredicto": j["veredicto"], "justificacion": j["justificacion"],
        })

    salida = os.path.join(aca, f"resultados_{date.today().isoformat()}.csv")
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    total = len(filas)
    ok = sum(1 for x in filas if x["veredicto"] in ("correcta", "fallback_correcto"))
    graves = [x for x in filas if x["veredicto"] in ("inventada", "fallback_incorrecto")]
    canarias_mal = [x for x in filas if x["tipo"] == "canaria" and x["veredicto"] != "fallback_correcto"]
    print(f"\n{ok}/{total} correctas. Resultados: {salida}")
    if canarias_mal:
        print(f"⚠️  CANARIAS FALLADAS ({len(canarias_mal)}): el grounding necesita ajuste "
              f"ANTES que cualquier otra cosa -> {[x['n'] for x in canarias_mal]}")
    if graves:
        print(f"🔴 Revisar a mano: {[x['n'] for x in graves]}")


if __name__ == "__main__":
    sys.exit(main())
