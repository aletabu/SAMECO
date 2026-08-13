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

import json
import re
import sys

from google.cloud import storage
from google import genai
from google.genai import types

# ----- Configuración (ajustar a tu sandbox / proyecto SAMECO) -----
PROJECT_ID = "sameco-conf-2026"
LOCATION = "us-central1"          # región para llamar a Gemini en Vertex
BUCKET = "CAMBIAR-nombre-del-bucket"
CARPETAS = ["evento/", "historico/"]
MODELO = "gemini-2.5-flash"       # estable y barato; alcanza de sobra para fichas

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
    },
    "required": ["titulo", "anio", "autores", "sector", "tema", "resumen"],
}

INSTRUCCION = (
    "Sos un bibliotecario técnico. Leé el documento adjunto y completá su ficha "
    "bibliográfica. Datos que no consten en el documento: no los inventes (año 0, "
    "lista vacía o cadena vacía según corresponda). El resumen debe ser fiel al "
    "contenido, en castellano."
)


def slug(nombre):
    s = re.sub(r"[^a-z0-9]+", "-", nombre.lower())
    return re.sub(r"-+", "-", s).strip("-")[:60]


def main():
    gcs = storage.Client(project=PROJECT_ID)
    ia = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    bucket = gcs.bucket(BUCKET)

    for carpeta in CARPETAS:
        salida = carpeta.rstrip("/") + ".metadata.jsonl"
        lineas = []
        for blob in bucket.list_blobs(prefix=carpeta):
            ext = "." + blob.name.rsplit(".", 1)[-1].lower() if "." in blob.name else ""
            if ext not in MIMES:
                continue
            print(f"Analizando {blob.name} …", flush=True)
            contenido = blob.download_as_bytes()
            respuesta = ia.models.generate_content(
                model=MODELO,
                contents=[
                    types.Part.from_bytes(data=contenido, mime_type=MIMES[ext]),
                    INSTRUCCION,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ESQUEMA_FICHA,
                ),
            )
            ficha = json.loads(respuesta.text)
            print(f"  → {ficha['titulo']} ({ficha['anio']}) · {ficha['tema']}")
            lineas.append(json.dumps({
                "id": slug(blob.name),
                "structData": ficha,
                "content": {"mimeType": MIMES[ext], "uri": f"gs://{BUCKET}/{blob.name}"},
            }, ensure_ascii=False))

        with open(salida, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
        print(f"\n{salida}: {len(lineas)} fichas. REVISALAS A MANO antes de importar.\n")

    print("Siguiente paso: subir los .jsonl al bucket (fuera de las carpetas de docs,")
    print("p. ej. gs://%s/metadata/) y en el datastore usar Import data →" % BUCKET)
    print("Cloud Storage → 'JSONL con metadatos'. Usar modo FULL si los documentos ya")
    print("estaban importados sin ficha (los IDs autogenerados viejos no coinciden con")
    print("estos y el modo incremental duplicaría).")


if __name__ == "__main__":
    sys.exit(main())
