# Plan del curso — Asistente Q&A SAMECO

Guion de las 4 sesiones de 1,5 h comprometidas en la propuesta v2 (sección 7), para un equipo **no técnico** de ~4 personas, más el trabajo tuyo entre sesiones. Cada sesión indica qué documento existente la respalda y qué material de esta carpeta usar.

**Ruta de preparación tuya (antes de la Sesión 1):**
1. Leer `02_Mapa_Azure_a_Google.md` (traduce lo que ya sabés de Azure).
2. Hacer completo el lab `01_Lab_Entorno_Practica.md` en tu proyecto sandbox.
3. Leer `04_Actualizacion_2026_Nombres_y_Costos.md` (nombres y precios vigentes; trae una corrección al rango del portal interno y la pregunta clave sobre Workspace).
4. Tener el sandbox **vivo** el día de cada sesión: todas las demos se hacen sobre tu entorno hasta que el de SAMECO esté listo.

**Regla didáctica transversal** (equipo no técnico): cero código en pantalla salvo la demo opcional de la Sesión 4. Cada concepto se ancla en una analogía de biblioteca: datastore = biblioteca, indexación = fichar los libros, el agente = el bibliotecario que solo responde con lo que hay en los estantes y te dice de qué libro lo sacó.

---

## Sesión 1 — Conceptos y descubrimiento (1,5 h)

**Respaldo:** Guía Técnica Parte C + Guía de Capacitación §1. **Objetivo:** que entiendan qué van a construir y salir con el inventario de contenidos encaminado.

| Min | Bloque | Contenido |
|---|---|---|
| 0–10 | Qué vamos a construir | Demo en vivo de TU sandbox ya funcionando: hacés 3 preguntas (una de evento, una de histórico, una que no está → fallback). Ver el final antes de empezar motiva más que cualquier teoría. |
| 10–35 | Los 4 conceptos | LLM y alucinación → RAG (buscar primero, responder después) → grounding y citas → contexto. Analogía del bibliotecario. Mostrar UNA alucinación real (preguntarle a un chat genérico por la agenda de SAMECO) — es el momento "ahh" de la sesión. |
| 35–50 | El diseño | 1 agente + 2 bibliotecas ("Evento" / "Histórico"). Por qué no dos agentes. Desde dónde se usará: widget público vs. uso interno. **Preguntar: ¿tienen Google Workspace?** (define la fuente: Drive o Cloud Storage — ver `04_Actualizacion…` §3). |
| 50–80 | Inventario de contenidos | Taller con planilla compartida: qué documentos existen, formato, ubicación, estado (texto limpio / PPT / escaneo / lámina). Clasificar por el semáforo de la propuesta §4: entra directo / necesita OCR / necesita descripción. Priorizar: lo más consultado primero. |
| 80–90 | Cierre y tareas | Tarea del equipo: completar el inventario y juntar los archivos en una carpeta. Tuya: crear el proyecto GCP de SAMECO. |

**Entre sesiones:** creás proyecto, billing con alerta, estructura del bucket (y/o Drive si hay Workspace), y cargás un primer lote de documentos "fáciles" para que la Sesión 2 arranque con algo real.

## Sesión 2 — Preparación del material y carga (1,5 h)

**Respaldo:** propuesta §4 + Capacitación Embeddings Parte 1–2 (solo las ideas, sin código). **Objetivo:** que sepan dejar la biblioteca lista y entiendan por qué un documento "entra mal".

| Min | Bloque | Contenido |
|---|---|---|
| 0–15 | Repaso + estado del inventario | Revisar la planilla; resolver dudas de clasificación. |
| 15–40 | Por qué no todo entra igual | Extracción de texto por formato: Word/PDF con texto (directo), PPT (texto sí, imagen no), escaneos (OCR), láminas (hay que describirlas). **Demo con el escaneo simulado de 2009 del sandbox**: mostrás el PDF (no se puede seleccionar texto) y el agente respondiendo igual gracias al OCR. |
| 40–70 | Carga en vivo | Con SU material real: subir documentos a la fuente elegida, crear/actualizar los 2 datastores (histórico con OCR parser), ver la indexación en curso. Que **una persona del equipo maneje el mouse**, no vos — acá empieza la transferencia. |
| 70–85 | El procedimiento "sumar un documento" | Ensayar el flujo del día después: subir → esperar indexación → verificar con una pregunta. Cronometrar. Este flujo es el corazón de la autonomía del equipo. |
| 85–90 | Tareas | Equipo: terminar de cargar el material fácil; separar escaneos/láminas problemáticos. Tuya: OCR/descripciones del material difícil. |

**Entre sesiones:** procesás el material difícil (OCR de escaneos deteriorados, descripciones de láminas A3 con IA multimodal), completás la indexación y creás la app conectada a los 2 datastores.

## Sesión 3 — El asistente en marcha: prompt y pruebas (1,5 h)

**Respaldo:** Guía de Capacitación §2 (diseño del prompt) — es EL documento de esta sesión. **Objetivo:** que sepan evaluar respuestas e iterar el comportamiento.

| Min | Bloque | Contenido |
|---|---|---|
| 0–10 | El asistente ya responde | Preview de la app de SAMECO con su material real. |
| 10–30 | Anatomía del comportamiento | Las 4 decisiones del prompt: rol, tono, grounding/fallback, contexto. Mostrar el con/sin preamble que ensayaste en el lab (paso 7): misma pregunta, dos comportamientos. |
| 30–70 | Taller: set de preguntas reales | Armar SU set de 15–20 preguntas (plantilla: `03_Set_Preguntas_Prueba.md`, bloques A/B/C — incluir las "canarias" de alucinación y las de enrutamiento evento/histórico). Correrlas en vivo, anotar en planilla: correcta / incompleta / inventada / fallback. |
| 70–85 | Iterar | Elegir la peor falla, ajustar UNA cosa (instrucción o documento fuente), volver a correr. Regla: un cambio por iteración. Que vean el ciclo completo una vez. |
| 85–90 | Tareas | Equipo: correr el set completo durante la semana y anotar fallas. Tuya: ajustes de prompt/fuentes según la planilla. |

**Entre sesiones:** afinás prompt y fuentes con la planilla de fallas, dejás la calidad estable y preparás el canal de publicación (widget con dominio del sitio de SAMECO allowlisteado, o portal según lo decidido).

## Sesión 4 — Publicación, entrega y "cómo funciona por dentro" (1,5 h)

**Respaldo:** propuesta §6 (entregables) + Capacitación Embeddings (demo opcional). **Objetivo:** asistente publicado y equipo autónomo.

| Min | Bloque | Contenido |
|---|---|---|
| 0–20 | Publicación en vivo | Pegar el snippet del widget en el sitio (o una página de prueba del dominio real). Primera consulta pública: momento ceremonial, dejá que la haga el equipo. |
| 20–45 | Manual de operación | Recorrer la documentación de uso que entregás: sumar un documento, verificar que impactó, qué hacer si una respuesta está mal (¿falta el doc? ¿está mal escaneado? ¿hay que ajustar una instrucción? → cuándo llamarte), vaciar/actualizar contenido ante cambios de agenda. |
| 45–60 | Costos y monitoreo | Dónde ver el gasto (Billing), qué esperar según `04_Actualizacion…` §2 (free tier de consultas, el matiz de las respuestas avanzadas, índice <10 GiB = $0), la alerta de presupuesto ya configurada. |
| 60–80 | Demo opcional "por dentro" | Si el grupo tiene curiosidad: la mini-demo RAG de la Guía Técnica B.5 (chunking → embeddings → retrieval) en 15 min, como espectáculo, no como clase. Mensaje: "esto es lo que la plataforma hace sola; existir, existe". |
| 80–90 | Cierre formal | Checklist de entrega (Guía de Capacitación §4): conceptos ✓ prompt ✓ set de pruebas ✓ costos ✓. Acordar canal de soporte post-entrega. |

---

## Mapa de materiales

| Documento | Rol en el curso |
|---|---|
| `Propuesta_Asesoria_Agente_QA_v2.docx` *(local, fuera del repo)* | Contrato y alcance; §4 es guion de la Sesión 2 |
| `Guia_Tecnica_Agente_QA_Vertex_1.docx` *(local; reemplazada por `instructivos/01` + `instructivos/00`, salvo la mini-demo RAG B.5)* | Parte B.5 = demo opcional Sesión 4 |
| `Guia_Capacitacion_Agente_QA.docx` *(local; conceptos absorbidos en `instructivos/00`)* | Guion Sesión 3 (prompt, iteración, caché) y checklist de cierre |
| `Capacitacion_Tecnica_Embeddings_Contexto.docx` *(local)* | Material de la demo opcional (Sesión 4) y tu propio estudio |
| `curso/instructivos/00_Conceptos_basicos.md` | Conceptos base para alumnos (LLM, RAG, grounding, datastore, contexto + pipeline interno) |
| `curso/01_Lab_Entorno_Practica.md` | Tu práctica previa en sandbox |
| `curso/02_Mapa_Azure_a_Google.md` | Tu traducción Azure → Google |
| `curso/03_Set_Preguntas_Prueba.md` | Plantilla del set de pruebas (sandbox y SAMECO) |
| `curso/04_Actualizacion_2026_Nombres_y_Costos.md` | Cifras y nombres vigentes; correcciones a la propuesta |
| `curso/material_practica/` | Documentos ficticios para el sandbox (evento + histórico + escaneo 2009) |
| `curso/instructivos/04_Enriquecimiento_fichas_metadata.md` | Enriquecimiento con fichas de metadatos (el "fine-tuning" del RAG), incl. campo `url` de descarga pública — parte del entregable, trabajo entre Sesión 2 y 3 |
| `curso/instructivos/03_QA_y_evaluacion.md` | Metodología de QA: set de 4 tipos de pregunta, escala de anotación y corrida automática |
| `curso/scripts/generar_fichas.py` | Script del análisis semántico: genera el JSONL de fichas (con URL de descarga) |
| `curso/scripts/correr_set_pruebas.py` + `set_pruebas.json` | Corredor automático del set contra la Answer API + juez Gemini → CSV de resultados |
| `curso/slides/` | Los 4 PPT de las sesiones (`generar_pptx.py` es la fuente; editar y regenerar) |
| `curso/instructivos/` | Instructivos para alumnos: A = app de búsqueda + widget (el entregable), B = agente propio con Agent Studio (fase 2 / comparativa) |
| `curso/widget/` | Página de demo comparativa (widget oficial + chat del Bibliotecario) y su `servidor_demo.py` |

## Riesgos a tener a mano

1. **¿Workspace sí o no?** — la pregunta de la Sesión 1 que define la fuente de datos y el canal interno (detalle en `04_…` §3).
2. **La consola cambió de nombre otra vez** — abrí la consola la mañana de cada sesión y verificá rutas; los docs oficiales están en transición "Agent Search".
3. **Indexación lenta en vivo** — nunca cargues material por primera vez durante una sesión sin un plan B: tené tu sandbox listo para mostrar mientras el de SAMECO indexa.
4. **Escaneos muy deteriorados** — gestionar expectativa desde la Sesión 2 con el semáforo de la propuesta §4; los ilegibles van a transcripción manual o a segunda tanda.
5. **Caché de respuestas** (Guía de Capacitación §3) — es optimización para DESPUÉS del evento si el tráfico lo justifica; no lo prometas para el go-live, requiere desarrollo por fuera de la plataforma gestionada.
