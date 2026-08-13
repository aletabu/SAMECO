# Análisis semántico + generación de fichas (metadatos) para el RAG de SAMECO.
#
# Recorre los documentos del bucket, le pide a Gemini una ficha estructurada por
# documento (título, año, autores, sector, tema, resumen) y escribe un JSONL por
# carpeta listo para importar al datastore ("Documentos con metadatos (RAG)").
# Gemini lee el archivo completo (multimodal): también funciona con escaneos.
#
# Requisitos (una vez):
#   pip3 install --user google-cloud-storage google-genai
#   gcloud auth application-default login
#
# Uso:
#   python3 generar_fichas.py
#   → genera evento.metadata.jsonl e historico.metadata.jsonl en esta carpeta
#   → revisar las fichas a mano (¡el paso humano importa!) y luego importar:
#     datastore → Import data → Cloud Storage → "JSONL con metadatos",
#     modo FULL para no duplicar IDs (ver nota al final del script).

import io
import json
import re
import sys
import time

import docx
from google.cloud import storage
from google import genai
from google.genai import types

# ----- Configuración (ajustar a tu sandbox / proyecto SAMECO) -----
PROJECT_ID = "sameco-conf-2026"
LOCATION = "us-central1"          # región para llamar a Gemini en Vertex
BUCKET = "sameco-sandbox-docs-alejandro"   # sandbox; cambiar para otro proyecto
CARPETAS = ["evento/", "historico/"]
MODELO = "gemini-2.5-flash"       # estable y barato; alcanza de sobra para fichas

# Base de la URL pública de descarga que va en la ficha (campo "url").
# Opciones: objetos públicos del bucket (default) o los documentos ya
# publicados en el sitio de la organización. Dejar en None para omitir el campo.
URL_PUBLICA_BASE = f"https://storage.googleapis.com/{BUCKET}/"

MIMES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/plain",
}

ESQUEMA_FICHA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "anio": {"type": "INTEGER", "description": "Año del documento o del trabajo; 0 si no consta"},
        "autores": {"type": "ARRAY", "items": {"type": "STRING"}},
        "sector": {"type": "STRING", "description": "Sector/industria: metalúrgica, alimentaria, salud, evento, etc."},
        "tema": {"type": "STRING", "description": "Tema principal en 2-4 palabras: 5S, SMED, kaizen, agenda, inscripción…"},
        "resumen": {"type": "STRING", "description": "Resumen fiel en castellano, 2-3 oraciones, sin inventar datos"},
        "etiquetas": {"type": "ARRAY", "items": {"type": "STRING"},
                      "description": "3 a 5 etiquetas temáticas en minúsculas (herramientas, sector, tipo de contenido)"},
    },
    "required": ["titulo", "anio", "autores", "sector", "tema", "resumen", "etiquetas"],
}

ESQUEMA_TAXONOMIA = {
    "type": "OBJECT",
    "properties": {
        "asignaciones": {"type": "ARRAY", "items": {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "sector": {"type": "STRING"},
                "tema": {"type": "STRING"},
                "etiquetas": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["id", "sector", "tema", "etiquetas"],
        }},
    },
    "required": ["asignaciones"],
}

INSTRUCCION = (
    "Sos un bibliotecario técnico. Leé el documento adjunto y completá su ficha "
    "bibliográfica. Datos que no consten en el documento: no los inventes (año 0, "
    "lista vacía o cadena vacía según corresponda). El resumen debe ser fiel al "
    "contenido, en castellano."
)


PAUSA_SEG = 13   # cuota del free trial: ~5 requests/min → espaciar llamadas


def generar(ia, contents, schema):
    """Llamada a Gemini con reintentos ante 429 (cuota por minuto del free trial)."""
    for intento in range(4):
        try:
            return ia.models.generate_content(
                model=MODELO, contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema))
        except Exception as e:
            if "429" in str(e) and intento < 3:
                espera = 30 * (intento + 1)
                print(f"  (cuota agotada, reintento en {espera}s)")
                time.sleep(espera)
            else:
                raise


def slug(nombre):
    s = re.sub(r"[^a-z0-9]+", "-", nombre.lower())
    return re.sub(r"-+", "-", s).strip("-")[:60]


def normalizar_etiquetas(ia, docs):
    """Fase 2 (curador): unifica sector/tema/etiquetas en un vocabulario consistente."""
    resumen = [{"id": d["id"], "sector": d["ficha"]["sector"], "tema": d["ficha"]["tema"],
                "etiquetas": d["ficha"]["etiquetas"]} for d in docs]
    prompt = (
        "Sos el curador de la taxonomía de una biblioteca técnica de mejora continua. "
        "Estas son las etiquetas propuestas documento por documento (inconsistentes "
        "entre sí). Unificá el vocabulario: sinónimos bajo UNA sola forma canónica "
        "(misma etiqueta = mismo string exacto), todo en castellano y minúsculas, "
        "3 a 5 etiquetas por documento, y sector/tema de una lista corta y coherente. "
        "No inventes contenido nuevo: solo consolidá lo propuesto.\n\n"
        + json.dumps(resumen, ensure_ascii=False)
    )
    r = generar(ia, prompt, ESQUEMA_TAXONOMIA)
    return {a["id"]: a for a in json.loads(r.text)["asignaciones"]}


def main():
    gcs = storage.Client(project=PROJECT_ID)
    ia = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    bucket = gcs.bucket(BUCKET)

    # Fase 1 — bibliotecario: una ficha por documento
    docs = []
    for carpeta in CARPETAS:
        blobs = [b for b in bucket.list_blobs(prefix=carpeta)
                 if "." in b.name and "." + b.name.rsplit(".", 1)[-1].lower() in MIMES]
        # si un documento está en dos formatos (p. ej. .docx y .md), fichar uno solo
        con_formato_rico = {b.name.rsplit(".", 1)[0] for b in blobs
                            if not b.name.lower().endswith((".md", ".txt"))}
        for blob in blobs:
            ext = "." + blob.name.rsplit(".", 1)[-1].lower()
            if ext in (".md", ".txt") and blob.name.rsplit(".", 1)[0] in con_formato_rico:
                print(f"Salteando {blob.name} (duplicado de otro formato)")
                continue
            print(f"Analizando {blob.name} …", flush=True)
            contenido = blob.download_as_bytes()
            # Gemini acepta PDF y texto como adjunto; DOCX se convierte a texto acá
            if ext == ".docx":
                d = docx.Document(io.BytesIO(contenido))
                parte = "\n".join(p.text for p in d.paragraphs if p.text.strip())
            elif ext in (".txt", ".md"):
                parte = contenido.decode("utf-8", errors="replace")
            else:  # .pdf entero, por visión (cubre escaneos sin OCR previo)
                parte = types.Part.from_bytes(data=contenido, mime_type=MIMES[ext])
            respuesta = generar(ia, [parte, INSTRUCCION], ESQUEMA_FICHA)
            time.sleep(PAUSA_SEG)
            ficha = json.loads(respuesta.text)
            if URL_PUBLICA_BASE:
                ficha["url"] = URL_PUBLICA_BASE + blob.name
            print(f"  → {ficha['titulo']} ({ficha['anio']}) · {ficha['etiquetas']}")
            docs.append({"id": slug(blob.name), "carpeta": carpeta,
                         "ficha": ficha, "mime": MIMES[ext],
                         "uri": f"gs://{BUCKET}/{blob.name}"})

    # Fase 2 — curador: normalizar etiquetas/sector/tema entre TODOS los docs
    print("\nNormalizando taxonomía entre documentos …")
    canon = normalizar_etiquetas(ia, docs)
    for d in docs:
        if d["id"] in canon:
            d["ficha"].update({k: canon[d["id"]][k] for k in ("sector", "tema", "etiquetas")})
    vocabulario = sorted({e for d in docs for e in d["ficha"]["etiquetas"]})
    print(f"Vocabulario final ({len(vocabulario)}): {', '.join(vocabulario)}")

    # Escritura de los JSONL por carpeta
    for carpeta in CARPETAS:
        salida = carpeta.rstrip("/") + ".metadata.jsonl"
        lineas = [json.dumps({"id": d["id"], "structData": d["ficha"],
                              "content": {"mimeType": d["mime"], "uri": d["uri"]}},
                             ensure_ascii=False)
                  for d in docs if d["carpeta"] == carpeta]
        with open(salida, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
        print(f"{salida}: {len(lineas)} fichas. REVISALAS A MANO antes de importar.")

    print("Siguiente paso: subir los .jsonl al bucket (fuera de las carpetas de docs,")
    print("p. ej. gs://%s/metadata/) y en el datastore usar Import data →" % BUCKET)
    print("Cloud Storage → 'JSONL con metadatos'. Usar modo FULL si los documentos ya")
    print("estaban importados sin ficha (los IDs autogenerados viejos no coinciden con")
    print("estos y el modo incremental duplicaría).")


if __name__ == "__main__":
    sys.exit(main())
