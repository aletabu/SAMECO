# Convierte videos de YouTube en documentos indexables para la biblioteca.
#
# Por cada URL de videos.txt, Gemini MIRA el video (entrada multimodal por URL,
# sin descargar nada) y produce: ficha bibliográfica + resumen estructurado por
# secciones con marcas de tiempo. Salida:
#   videos_docs/<slug>.md        → el documento a subir al bucket (carpeta videos/)
#   videos.metadata.jsonl        → las fichas, con url = el link de YouTube
#
# Flujo completo: revisar los .md a mano → subirlos a gs://BUCKET/videos/ →
# subir el JSONL a gs://BUCKET/metadata/ → Import data ("JSONL con metadatos").
# El asistente citará el contenido y ofrecerá "Ver el video" con el link real.
#
# Requisitos: los de generar_fichas.py (google-genai + ADC).
# Uso: python3 generar_transcripciones.py   (lee videos.txt de esta carpeta)

import json
import os
import re
import sys
import time

from google import genai
from google.genai import types

PROJECT_ID = "sameco-conf-2026"
LOCATION = "global"
BUCKET = "sameco-sandbox-docs-alejandro"
MODELO = "gemini-2.5-flash"
PAUSA_SEG = 13   # cuota free trial ~5 req/min

ESQUEMA_VIDEO = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "anio": {"type": "INTEGER", "description": "Año del contenido si consta o se dice; 0 si no"},
        "oradores": {"type": "ARRAY", "items": {"type": "STRING"},
                     "description": "Personas que hablan, con nombre y rol si constan"},
        "sector": {"type": "STRING"},
        "tema": {"type": "STRING", "description": "Tema principal en 2-4 palabras"},
        "etiquetas": {"type": "ARRAY", "items": {"type": "STRING"},
                      "description": "3 a 5 etiquetas en minúsculas y castellano"},
        "resumen": {"type": "STRING", "description": "Resumen fiel, 3-4 oraciones"},
        "secciones": {"type": "ARRAY", "items": {
            "type": "OBJECT",
            "properties": {
                "inicio": {"type": "STRING", "description": "Marca de tiempo MM:SS"},
                "titulo": {"type": "STRING"},
                "contenido": {"type": "STRING",
                              "description": "Lo dicho en la sección, fiel y detallado, en prosa"},
            },
            "required": ["inicio", "titulo", "contenido"],
        }},
    },
    "required": ["titulo", "anio", "oradores", "sector", "tema", "etiquetas", "resumen", "secciones"],
}

INSTRUCCION = (
    "Mirá este video institucional/técnico y armá su documento de biblioteca en "
    "castellano: ficha (título, año si consta, oradores, sector, tema, etiquetas), "
    "resumen fiel, y secciones con marca de tiempo (MM:SS) cubriendo TODO el "
    "contenido hablado. Sé fiel a lo que se dice: no agregues información externa "
    "ni opinión. Si un dato no consta, dejalo vacío o en 0."
)


def slug(texto):
    s = re.sub(r"[^a-z0-9]+", "-", texto.lower())
    return re.sub(r"-+", "-", s).strip("-")[:60]


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{6,})", url)
    return m.group(1) if m else slug(url)


def main():
    aca = os.path.dirname(os.path.abspath(__file__))
    lista = os.path.join(aca, "videos.txt")
    if not os.path.exists(lista):
        print("Creá videos.txt con una URL de YouTube por línea."); return 1
    urls = [l.strip() for l in open(lista, encoding="utf-8")
            if l.strip() and not l.startswith("#")]

    ia = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    outdir = os.path.join(aca, "videos_docs")
    os.makedirs(outdir, exist_ok=True)
    fichas = []

    for url in urls:
        print(f"Mirando {url} …", flush=True)
        try:
            r = ia.models.generate_content(
                model=MODELO,
                contents=[types.Part.from_uri(file_uri=url, mime_type="video/mp4"),
                          INSTRUCCION],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ESQUEMA_VIDEO),
            )
        except Exception as e:
            print(f"  ERROR con {url}: {str(e)[:200]}")
            continue
        d = json.loads(r.text)
        nombre = f"video-{slug(d['titulo']) or video_id(url)}"
        cuerpo = [f"# {d['titulo']}", "",
                  f"Video del canal de SAMECO: {url}",
                  f"Oradores: {', '.join(d['oradores']) or 'no consta'}  ·  "
                  f"Año: {d['anio'] or 'no consta'}  ·  Tema: {d['tema']}", "",
                  f"## Resumen", d["resumen"], "", "## Contenido por secciones", ""]
        for s in d["secciones"]:
            cuerpo += [f"### [{s['inicio']}] {s['titulo']}", s["contenido"], ""]
        ruta = os.path.join(outdir, nombre + ".md")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(cuerpo))
        ficha = {k: d[k] for k in ("titulo", "anio", "oradores", "sector",
                                   "tema", "etiquetas", "resumen")}
        ficha["tipo_material"] = "video"
        ficha["url"] = url   # la descarga/visualización ES el video de YouTube
        fichas.append(json.dumps({
            "id": nombre,
            "structData": ficha,
            "content": {"mimeType": "text/plain",
                        "uri": f"gs://{BUCKET}/videos/{nombre}.md"},
        }, ensure_ascii=False))
        print(f"  → {d['titulo']} · {len(d['secciones'])} secciones · {ruta}")
        time.sleep(PAUSA_SEG)

    if fichas:
        salida = os.path.join(aca, "videos.metadata.jsonl")
        with open(salida, "w", encoding="utf-8") as f:
            f.write("\n".join(fichas) + "\n")
        print(f"\n{salida}: {len(fichas)} fichas. Revisar los .md, subirlos a "
              f"gs://{BUCKET}/videos/ e importar el JSONL (modo FULL junto con "
              f"las demás fichas de la carpeta).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
