# Corre el set de pruebas de SAMECO (set_pruebas_sameco.json, 59 casos) contra
# el chat PUBLICADO en Cloud Run y califica cada respuesta con un juez Gemini
# que usa los criterios del equipo: esperado + DEBE + NO DEBE.
#
# Salida: resultados_sameco_<fecha>.csv con las columnas de la planilla del
# equipo (¿Usó el data store? / ¿Citó GM correcto? / Resultado / Notas).
#
# El juez corre en el sandbox (sameco-conf-2026) con ADC; el chat es la URL
# pública, no necesita credenciales. Cuota free trial → pausa entre llamadas.
#
# Uso: python3 correr_set_sameco.py

import csv
import json
import os
import sys
import time
from datetime import date

import requests
from google import genai
from google.genai import types

URL_CHAT = "https://sami-chat-929656340238.us-west1.run.app/api/chat"
PROYECTO_JUEZ = "sameco-conf-2026"   # el juez corre en el sandbox de Alejandro
MODELO_JUEZ = "gemini-2.5-flash"
PAUSA_SEG = 13   # cuota free trial ~5 req/min

ESQUEMA_JUEZ = {
    "type": "OBJECT",
    "properties": {
        "resultado": {"type": "STRING", "enum": ["Aprueba", "Parcial", "Desaprueba"]},
        "cito_gm": {"type": "STRING", "enum": ["sí", "no", "no aplica"]},
        "notas": {"type": "STRING", "description": "Una o dos oraciones: qué cumplió y qué falló"},
    },
    "required": ["resultado", "cito_gm", "notas"],
}

INSTR_JUEZ = (
    "Sos el juez de QA de un asistente bibliotecario. Compará la RESPUESTA del "
    "asistente con lo ESPERADO, lo que DEBE cumplir y lo que NO DEBE hacer.\n"
    "- Aprueba: cumple lo esperado y el DEBE, sin caer en el NO DEBE.\n"
    "- Parcial: encaminada pero omite parte del DEBE o de los datos esperados.\n"
    "- Desaprueba: cae en el NO DEBE, contradice lo esperado o inventa datos.\n"
    "Información ADICIONAL plausible del documento NO la invalida. "
    "cito_gm: 'sí' si menciona el/los GM correctos o identifica inequívocamente "
    "la organización correcta; 'no aplica' si el caso no refiere a un GM (—)."
)


def preguntar(mensajes, cliente):
    r = requests.post(URL_CHAT, json={"cliente": cliente, "mensajes": mensajes},
                      timeout=180)
    r.raise_for_status()
    d = r.json()
    return d.get("texto", ""), d.get("fuentes", [])


def juzgar(ia, caso, respuesta, fuentes):
    prompt = (
        f"{INSTR_JUEZ}\n\nPREGUNTA: {caso['pregunta']}\n\n"
        f"ESPERADO: {caso['esperado']}\n\nDEBE: {caso['debe']}\n\n"
        f"NO DEBE: {caso['no_debe']}\n\nGM correcto(s): {caso['gm']}\n\n"
        f"RESPUESTA DEL ASISTENTE:\n{respuesta}\n\n"
        f"FUENTES CITADAS POR EL SISTEMA: {', '.join(fuentes) or '(ninguna)'}"
    )
    for intento in range(4):
        try:
            r = ia.models.generate_content(
                model=MODELO_JUEZ, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ESQUEMA_JUEZ))
            return json.loads(r.text)
        except Exception as e:
            if "429" in str(e) and intento < 3:
                espera = 30 * (intento + 1)
                print(f"  (cuota del juez agotada, reintento en {espera}s)", flush=True)
                time.sleep(espera)
            else:
                return {"resultado": "SIN JUEZ", "cito_gm": "no aplica",
                        "notas": f"error del juez: {str(e)[:120]}"}


def main():
    aca = os.path.dirname(os.path.abspath(__file__))
    casos = json.load(open(os.path.join(aca, "set_pruebas_sameco.json"),
                           encoding="utf-8"))
    ia = genai.Client(vertexai=True, project=PROYECTO_JUEZ, location="global")
    salida = os.path.join(aca, f"resultados_sameco_{date.today()}.csv")
    respuestas = {}   # n -> (pregunta, respuesta) para encadenar seguimientos
    resumen = {"Aprueba": 0, "Parcial": 0, "Desaprueba": 0, "SIN JUEZ": 0}

    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n", "ID", "Categoría", "GM", "Dificultad", "Pregunta",
                    "Respuesta del agente", "Fuentes", "¿Usó el data store?",
                    "¿Citó GM correcto?", "Resultado", "Notas"])
        for caso in casos:
            mensajes = []
            if caso.get("sigue_a") and caso["sigue_a"] in respuestas:
                pq, pr = respuestas[caso["sigue_a"]]
                mensajes += [{"rol": "user", "texto": pq},
                             {"rol": "bot", "texto": pr}]
            mensajes.append({"rol": "user", "texto": caso["pregunta"]})
            print(f"[{caso['n']:2}/{len(casos)}] {caso['id']}: "
                  f"{caso['pregunta'][:60]}…", flush=True)
            try:
                respuesta, fuentes = preguntar(mensajes, f"qa-{caso['id']}")
            except Exception as e:
                respuesta, fuentes = f"[ERROR DEL CHAT: {str(e)[:120]}]", []
            respuestas[caso["n"]] = (caso["pregunta"], respuesta)
            veredicto = juzgar(ia, caso, respuesta, fuentes)
            resumen[veredicto["resultado"]] = resumen.get(veredicto["resultado"], 0) + 1
            w.writerow([caso["n"], caso["id"], caso["tipo"], caso["gm"],
                        caso["dificultad"], caso["pregunta"], respuesta,
                        " · ".join(fuentes), "sí" if fuentes else "no",
                        veredicto["cito_gm"], veredicto["resultado"],
                        veredicto["notas"]])
            f.flush()
            print(f"     → {veredicto['resultado']} · GM: {veredicto['cito_gm']} "
                  f"· {veredicto['notas'][:80]}", flush=True)
            time.sleep(PAUSA_SEG)

    print(f"\n{salida}")
    total = sum(resumen.values())
    for k, v in resumen.items():
        if v:
            print(f"  {k}: {v}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
