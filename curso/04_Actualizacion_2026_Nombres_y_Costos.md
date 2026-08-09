# Actualización ago-2026: nombres de producto y costos validados

Investigado el 05/08/2026 contra páginas oficiales de Google Cloud. Sirve para dos cosas: (a) corregir/confirmar la sección 9 de la propuesta antes de firmar, (b) tener las cifras frescas para cuando pregunten en las sesiones.

## 1. Nombres vigentes (qué decir en el curso)

| Nombre en la propuesta / guías | Nombre en docs (hoy) | Nombre en consola (hoy) |
|---|---|---|
| Vertex AI Search / Agent Builder | **Agent Search** (desde abr-2026) | **AI Applications** (`console.cloud.google.com/gen-app-builder/`) |
| Vertex AI (plataforma) | **Gemini Enterprise Agent Platform** | Secciones "Vertex AI" aún visibles |
| Agentspace / portal interno | **Gemini Enterprise** (producto por asiento) | Gemini Enterprise |
| — (API subyacente) | **Discovery Engine API** (nunca cambió) | — |

Frase para el curso: *"En la consola lo van a ver como AI Applications; en la documentación figura como Agent Search; en artículos viejos, Vertex AI Search o Agent Builder. Es todo lo mismo: la API de abajo se llama Discovery Engine y no cambió nunca."*

La nota de versiones de la Guía Técnica (que decía "Vertex AI Search se renombró Agent Search") **queda confirmada** y sigue vigente.

## 2. Costos validados vs. sección 9 de la propuesta

### OCR (costo único) — ✅ confirmado y mejor
- Enterprise Document OCR: **primeras 1.000 páginas/mes GRATIS**, luego **$1,50/1.000 páginas** (hasta 5M).
- La propuesta decía "$1,50 por 1.000 páginas": correcto, y además si el histórico se procesa en tandas de <1.000 páginas/mes puede salir $0.
- Ojo: si se usa el **Layout Parser** del datastore (el recomendado para RAG) el costo es mayor ($10/1.000 págs. como procesador Document AI). Para escaneos puros, el OCR parser alcanza.

### Indexación / almacenamiento — ✅ confirmado y mejor
- **$5,00/GiB/mes** con **10 GiB gratis por mes**.
- La propuesta estimaba "USD 5–10 mensuales para unos pocos GB". Realidad: **si la biblioteca queda bajo 10 GiB, el costo base es $0**. Podés dar esta noticia en la Sesión 1 — mejora la propuesta.

### Consultas (widget público) — ✅ confirmado, con un matiz importante
- Free tier: **10.000 consultas/mes gratis** por cuenta (permanente).
- Por encima: Standard $1,50/1.000; **Enterprise $4,00/1.000 — e incluye las respuestas generativas básicas ("core Generative Answers / AI Mode")**.
- **Matiz:** el add-on "Advanced Generative Answers" cuesta **+$4,00/1.000 consultas y NO está cubierto por el free tier**. Traducción práctica: las consultas se regalan, pero si activás las respuestas avanzadas (follow-ups sugeridos, consultas complejas, multimodal), cada 1.000 preguntas con respuesta avanzada cuestan ~$4 desde la primera. La estimación de la propuesta (~$0–40/mes según tráfico) **sigue siendo válida**: 10.000 consultas con respuesta avanzada = $40.
- Decisión de diseño barata: para el widget del evento puede alcanzar Enterprise con respuestas generativas core (incluidas en los $4/1.000, y las primeras 10.000 consultas del componente búsqueda gratis).

### Portal interno (Gemini Enterprise) — ✅ confirmado
- **Business: desde $21/asiento/mes** (1–300 asientos, prueba gratis 30 días, 25 GiB de índice por asiento). **Standard: desde $30/asiento/mes.**
- Para 4 personas: **$84–120/mes**. La propuesta decía "$21–84/mes": el piso real con 4 asientos Business es $84; corregir el rango si se mantiene esa opción.
- **Requiere cuentas de organización (Workspace)** — ver punto 3. Alternativa a costo cero: que las 4 personas usen el widget en una página interna, o el Preview de la consola.

### Modelos (referencia, por si preguntan)
- Familia Flash vigente: Gemini 3 Flash Preview $0,50/$3,00 por millón de tokens (entrada/salida); Gemini 2.5 Flash $0,30/$2,50. Pro: Gemini 3.1 Pro $2,00/$12,00.
- Embeddings (solo demo "por dentro"): gemini-embedding-001 $0,15/1M tokens; el clásico text-embedding-005 sigue listado como legacy ($0,000025/1.000 caracteres) — la demo Python de la guía técnica sigue funcionando, pero conviene mostrar `gemini-embedding-001`.

### Crédito de prueba — ✅ confirmado
- **$300 por 90 días**, requiere tarjeta (hold $0–1), solo cuentas nunca-pagas. Cubre Agent Search/Discovery Engine. No cubre Gemini API de AI Studio (no nos afecta: usamos la plataforma, no AI Studio).

## 3. El punto que obliga a revisar la propuesta: Google Drive requiere Workspace

La documentación oficial es explícita:
- El conector de Drive **no funciona con cuentas @gmail.com personales** (necesita Customer ID de Google Workspace).
- Los datastores de Drive tienen ACL y **no admiten widget con Public Access** → la web pública del evento debe alimentarse desde **Cloud Storage**.
- La búsqueda sobre Drive solo la pueden hacer usuarios logueados de la misma organización.

**Pregunta obligada para la Sesión 1: ¿SAMECO tiene Google Workspace?**

| Escenario | Diseño resultante |
|---|---|
| Tienen Workspace | Como la propuesta: Drive para el histórico interno + **espejo en Cloud Storage para lo que alimenta el widget público** |
| No tienen Workspace | Los 2 datastores desde Cloud Storage. La "biblioteca" del equipo es el bucket (se sube por navegador, es simple); documentar ese procedimiento en lugar del de Drive |

En ambos casos el diseño "1 agente + 2 datastores" queda intacto; cambia solo la fuente. La sección 6 de la propuesta menciona "conector de Google Drive" — conviene suavizarla a "conector de Drive o carga en Cloud Storage, según la cuenta que disponga SAMECO".

## 4. Otras confirmaciones útiles

- **OCR integrado al datastore**: no hace falta armar un pipeline de Document AI aparte; se activa el "OCR parser" en las opciones de procesamiento al crear el datastore (facturado como Document AI). Límite: OCR procesa las primeras 500 páginas de cada PDF.
- **PPTX**: lo procesan el digital parser y el layout parser (el OCR parser es solo PDF). El texto-como-imagen dentro de un PPT sigue sin leerse — la advertencia de la propuesta (sección 4) es correcta.
- **Widget**: estilo no personalizable por CSS; requiere allowlist de dominios; el modo "Search with an answer" muestra citas.
- **Preamble**: el "prompt del sistema" de la app se llama preamble y su ajuste fino es por API (`promptSpec.preamble` de la Answer API); la consola ofrece control limitado. Para el curso: el grueso del comportamiento se maneja igual (citas, fallback, modelo) desde Configurations.
