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

import csv
import difflib
import io
import json
import re
import subprocess
import sys
import time
import unicodedata

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


# ----- Mapeo opcional archivo→URL pública (CSV del equipo) -----
# Uso: --mapeo mapeo_urls_sameco.csv  → el campo "url" de cada ficha sale de
# la columna WEB de la fila que matchee con el archivo (y "video" de YOUTUBE).
# Un archivo sin fila en el mapeo queda SIN url (el agente no ofrece descarga).

def _normalizar(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    # fuera prefijos/decoraciones de nombre de archivo: "2026 GM08", "A3",
    # "31° Encuentro", extensión, números sueltos de versión
    s = re.sub(r"\.(pptx?|pdf|docx?)$", "", s)
    s = re.sub(r"\b20\d\d\b|\bgm\d+\b|\ba3\b|31.?\s*encuentro", " ", s)
    s = re.sub(r"[^a-z0-9ñ]+", " ", s)
    return " ".join(s.split())


def cargar_mapeo(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def emparejar(nombres, mapeo):
    """Asigna a cada archivo del bucket su fila del CSV por similitud de texto.

    Compara el nombre normalizado contra las columnas A3 y ORGANIZACION+NOMBRE
    (el máximo de ambas, así una celda A3 mal copiada no arruina el match).
    Devuelve {nombre: fila} y una lista de reportes para revisión humana."""
    puntajes = []
    for n in nombres:
        base = _normalizar(n.rsplit("/", 1)[-1])
        for i, fila in enumerate(mapeo):
            score = max(
                difflib.SequenceMatcher(None, base, _normalizar(fila["A3"])).ratio(),
                difflib.SequenceMatcher(
                    None, base,
                    _normalizar(fila["ORGANIZACION"] + " " + fila["NOMBRE"])).ratio(),
            )
            puntajes.append((score, n, i))
    puntajes.sort(reverse=True)
    asignado, usado, reporte = {}, set(), []
    for score, n, i in puntajes:   # greedy: mejores matches primero, únicos
        if n in asignado or i in usado:
            continue
        if score < 0.55:
            continue
        asignado[n] = mapeo[i]
        usado.add(i)
        reporte.append((score, n.rsplit("/", 1)[-1], mapeo[i]["ORGANIZACION"]))
    for n in nombres:
        if n not in asignado:
            reporte.append((0.0, n.rsplit("/", 1)[-1], "** SIN FILA EN EL CSV → sin url **"))
    for i, fila in enumerate(mapeo):
        if i not in usado:
            reporte.append((0.0, "** FILA SIN ARCHIVO EN EL BUCKET **", fila["ORGANIZACION"]))
    return asignado, sorted(reporte)


def credenciales_gcloud():
    """Credenciales desde `gcloud auth print-access-token` (la cuenta del CLI,
    p. ej. la de SAMECO) para leer un bucket al que el ADC local no accede."""
    from google.oauth2.credentials import Credentials
    token = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True).strip()
    return Credentials(token=token)


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
    # Flags opcionales (sin flags = sandbox, comportamiento original):
    #   --bucket B --carpeta C      otro bucket/carpeta (repetible --carpeta)
    #   --mapeo archivo.csv         urls públicas desde el CSV del equipo
    #   --storage-gcloud            leer el bucket con la cuenta del gcloud CLI
    #   --gemini-proyecto P         proyecto donde facturan las llamadas a Gemini
    #   --solo-mapeo                solo mostrar la tabla de matching y salir
    args = sys.argv[1:]
    def _flag(nombre, defecto=None):
        return args[args.index(nombre) + 1] if nombre in args else defecto
    bucket_nombre = _flag("--bucket", BUCKET)
    carpetas = ([args[i + 1] for i, a in enumerate(args) if a == "--carpeta"]
                or CARPETAS)
    mapeo_ruta = _flag("--mapeo")
    proyecto_gemini = _flag("--gemini-proyecto", PROJECT_ID)

    creds = credenciales_gcloud() if "--storage-gcloud" in args else None
    gcs = storage.Client(project=PROJECT_ID, credentials=creds) if creds \
        else storage.Client(project=PROJECT_ID)
    ia = genai.Client(vertexai=True, project=proyecto_gemini, location=LOCATION)
    bucket = gcs.bucket(bucket_nombre)

    mapeo, asignacion = None, {}
    if mapeo_ruta:
        mapeo = cargar_mapeo(mapeo_ruta)
        nombres = [b.name for c in carpetas for b in bucket.list_blobs(prefix=c)
                   if "." in b.name
                   and "." + b.name.rsplit(".", 1)[-1].lower() in MIMES]
        asignacion, reporte = emparejar(nombres, mapeo)
        print(f"Mapeo {mapeo_ruta}: {len(mapeo)} filas · {len(nombres)} archivos "
              f"· {len(asignacion)} matcheados\n")
        for score, archivo, org in reporte:
            print(f"  {score:.2f}  {archivo[:70]:70}  →  {org}")
        if "--solo-mapeo" in args:
            return 0
        print()

    # Fase 1 — bibliotecario: una ficha por documento
    docs = []
    for carpeta in carpetas:
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
            if mapeo is not None:
                fila = asignacion.get(blob.name)
                if fila:   # url de la página pública del sitio; video si hay
                    ficha["url"] = fila["WEB"]
                    if fila.get("YOUTUBE"):
                        ficha["video"] = fila["YOUTUBE"]
                # sin fila en el CSV → sin "url": el agente no ofrece descarga
            elif URL_PUBLICA_BASE:
                ficha["url"] = URL_PUBLICA_BASE + blob.name
            print(f"  → {ficha['titulo']} ({ficha['anio']}) · {ficha['etiquetas']}")
            docs.append({"id": slug(blob.name), "carpeta": carpeta,
                         "ficha": ficha, "mime": MIMES[ext],
                         "uri": f"gs://{bucket_nombre}/{blob.name}"})

    # Fase 2 — curador: normalizar etiquetas/sector/tema entre TODOS los docs
    print("\nNormalizando taxonomía entre documentos …")
    canon = normalizar_etiquetas(ia, docs)
    for d in docs:
        if d["id"] in canon:
            d["ficha"].update({k: canon[d["id"]][k] for k in ("sector", "tema", "etiquetas")})
    vocabulario = sorted({e for d in docs for e in d["ficha"]["etiquetas"]})
    print(f"Vocabulario final ({len(vocabulario)}): {', '.join(vocabulario)}")

    # Escritura de los JSONL por carpeta
    for carpeta in carpetas:
        salida = carpeta.rstrip("/") + ".metadata.jsonl"
        lineas = [json.dumps({"id": d["id"], "structData": d["ficha"],
                              "content": {"mimeType": d["mime"], "uri": d["uri"]}},
                             ensure_ascii=False)
                  for d in docs if d["carpeta"] == carpeta]
        with open(salida, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
        print(f"{salida}: {len(lineas)} fichas. REVISALAS A MANO antes de importar.")

    print("Siguiente paso: subir los .jsonl al bucket (fuera de las carpetas de docs,")
    print("p. ej. gs://%s/metadata/) y en el datastore usar Import data →" % bucket_nombre)
    print("Cloud Storage → 'JSONL con metadatos'. Usar modo FULL si los documentos ya")
    print("estaban importados sin ficha (los IDs autogenerados viejos no coinciden con")
    print("estos y el modo incremental duplicaría).")


if __name__ == "__main__":
    sys.exit(main())
