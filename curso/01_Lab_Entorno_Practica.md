# Lab: tu entorno de práctica en Google Cloud

Objetivo: que antes de la Sesión 1 con SAMECO hayas construido vos mismo, de punta a punta, una réplica del asistente (1 agente + 2 datastores) en un proyecto propio, usando el material ficticio de `material_practica/`. Tiempo estimado: 2 tardes (una para los pasos 1–6, otra para 7–10).

> **Nombres vigentes (verificado ago-2026):** el producto se llama **"Agent Search"** en la documentación (renombrado en Cloud Next abr-2026, dentro de la "Gemini Enterprise Agent Platform", ex Vertex AI), pero la consola sigue mostrando **"AI Applications"** y la URL es `console.cloud.google.com/gen-app-builder/`. La API subyacente sigue siendo **Discovery Engine API**. En el curso conviene decir: "lo van a ver como AI Applications en la consola; en los docs figura como Agent Search; antes se llamaba Vertex AI Search / Agent Builder".

---

## ⚠️ Hallazgo crítico antes de empezar (impacta la propuesta)

**El conector de Google Drive NO funciona con cuentas Gmail personales.** La documentación oficial es explícita: las cuentas de consumidor @gmail.com no tienen Customer ID de Workspace y no están soportadas. Además:

- Los datastores de Drive llevan control de acceso (ACL) por usuario de la organización, y **un datastore con ACL no admite el widget de "Public Access"**. Es decir: **el widget público del evento no puede servir contenido desde Drive** — debe alimentarse desde Cloud Storage (u otra fuente sin ACL).
- La búsqueda sobre Drive solo la pueden hacer usuarios de la misma organización Workspace.

Consecuencias prácticas:

1. **Para tu sandbox** (cuenta personal): practicá todo con **Cloud Storage**. El flujo es idéntico salvo la fuente.
2. **Para SAMECO**: hay que averiguar en la Sesión 1 si tienen Google Workspace. Si no tienen, el diseño "carpeta de Drive como biblioteca" de la propuesta se reemplaza por: carpeta de Drive (o local) como *staging* + subida al bucket de Cloud Storage como paso de publicación. Sigue siendo operable por no técnicos (la consola permite subir archivos al bucket por navegador), pero cambia el procedimiento de "sumar un documento nuevo" que vas a documentar.
3. El **portal interno con Gemini Enterprise** (por usuario/mes) también presupone cuentas de la organización. Si SAMECO no tiene Workspace, la alternativa interna simple es el mismo widget en una página privada, o el Preview de la consola para las 4 personas.

---

## Paso 1 — Cuenta y proyecto

1. Con tu cuenta Google, entrá a `console.cloud.google.com` y aceptá los términos.
2. Activá la **prueba gratuita**: USD 300 de crédito por 90 días (verificado ago-2026; pide tarjeta, hace un hold de USD 0–1, no cobra). El crédito **sí cubre** Agent Search/Discovery Engine. Requisito: no haber sido nunca cliente de pago de GCP.
3. Creá un proyecto nuevo: `sameco-sandbox` (anotá el **Project ID**, que es único y distinto del nombre).
4. **Equivalencia Azure:** el proyecto = suscripción + resource group en uno. Todo lo que hagas vive ahí, y al final borrás el proyecto entero (IAM & Admin → Settings → Shut down).

## Paso 2 — Presupuesto y alarma (hacelo antes que nada)

1. Menú ☰ → **Billing** → **Budgets & alerts** → Create budget.
2. Presupuesto: USD 20 para el sandbox, alertas a 50/90/100%.
3. Equivale a los Budgets de Cost Management en Azure. Con el free tier de 10.000 consultas/mes y material chico, el gasto real del lab debería ser de centavos — la alarma es para dormir tranquilo.

## Paso 3 — Habilitar el producto

1. En el buscador de la consola escribí **"AI Applications"** y entrá (URL directa: `console.cloud.google.com/gen-app-builder/`).
2. Clic en **"Continue and activate the API"** — habilita la Discovery Engine API automáticamente (no hace falta ir a la biblioteca de APIs).
3. Permisos: como Owner del proyecto ya tenés implícito el rol "Discovery Engine Admin".

## Paso 4 — Subir el material a Cloud Storage

1. Menú ☰ → **Cloud Storage** → **Buckets** → Create.
   - Nombre (global único): p. ej. `sameco-sandbox-docs-<tunombre>`
   - Región: `us` (multi-region) o `us-central1`. Anotá cuál elegiste.
2. Creá dos carpetas dentro del bucket: `evento/` e `historico/`.
3. Subí por el navegador (botón Upload):
   - A `evento/`: los 3 `.docx` de `material_practica/evento/`
   - A `historico/`: los 3 `.docx` de `material_practica/historico/` **+ el PDF escaneado** `trabajo_2009_escaneado_pintura.pdf`
4. Alternativa CLI (opcional, para tu versión reproducible):
   ```bash
   gcloud auth login
   gcloud config set project TU_PROJECT_ID
   gcloud storage buckets create gs://sameco-sandbox-docs-<tunombre> --location=us
   gcloud storage cp material_practica/evento/*.docx gs://sameco-sandbox-docs-<tunombre>/evento/
   gcloud storage cp material_practica/historico/*.docx material_practica/historico/*.pdf gs://sameco-sandbox-docs-<tunombre>/historico/
   ```

## Paso 5 — Crear los DOS datastores

En AI Applications → **Data Stores** → **Create data store**, dos veces:

**Datastore 1 — "evento-2026"**
1. Source: **Cloud Storage** → Folder → navegá a `evento/`.
2. Tipo de datos: **unstructured documents**.
3. Document processing options: dejá el **digital parser** (default) — es material moderno con texto.
4. Región: global. Nombre: `evento-2026`. Create.

**Datastore 2 — "trabajos-historicos"**
1. Source: **Cloud Storage** → Folder → `historico/`.
2. Tipo de datos: unstructured documents.
3. **Document processing options → activá el OCR parser** (o el layout parser, que es el recomendado para RAG y también procesa DOCX/PPTX — nota: OCR parser aplica solo a PDF; el layout/digital cubre el resto). Este es el paso que hace legible el escaneo de 2009. Ambos parsers avanzados tienen costo extra de Document AI, marginal para 7 documentos.
4. Nombre: `trabajos-historicos`. Create.

La importación tarda de minutos a una hora. Se ve el progreso en la pestaña Activity del datastore. Mientras indexa, tomate un café o repasá `03_Set_Preguntas_Prueba.md`.

> Known issue documentado: a veces la creación desde Cloud Storage falla por consola; el workaround oficial es crear el bucket desde la consola primero (ya lo hiciste) o usar la API.

## Paso 6 — Crear la app (el "agente")

1. AI Applications → **Apps** → **Create app** → tipo **Custom search**.
2. Activá los dos toggles: **Enterprise features** y **generative responses / advanced LLM features** (sin esto no hay respuestas redactadas con citas — y ojo: las respuestas generativas avanzadas se facturan aparte del free tier de consultas).
3. Nombre: `Asistente SAMECO (práctica)`. Company name: SAMECO. Location: **global**.
4. En la pantalla **Data stores**: seleccioná **los dos** (`evento-2026` y `trabajos-historicos`). Acá materializás el diseño "1 agente + 2 datastores" de la propuesta.

## Paso 7 — Configurar el comportamiento

1. App → **Configurations** → pestaña **UI**:
   - **Search Type**: probá primero **"Search with an answer"** (respuesta con citas sobre los resultados); después cambiá a **"Search with follow-ups"** para ver el modo conversacional (necesario para la pregunta 8 del set, "¿y el segundo día?").
   - Elegí el modelo en "LLMs for answers" (el Flash vigente alcanza y es el más barato).
2. El "prompt del sistema" acá se llama **preamble**. En consola el control es limitado; el ajuste fino es por API (campo `promptSpec.preamble` de la Answer API). Para el lab: probá primero sin preamble, después con uno tipo:
   > "Sos el asistente oficial de SAMECO. Respondé solo con la información de los documentos. Si no está, decilo y sugerí escribir a la organización. Español, breve, citando la fuente."
   
   y compará con el set de preguntas. Esa comparación con/sin preamble es oro didáctico para la Sesión 3.

## Paso 8 — Probar con el set de preguntas

1. App → **Preview**.
2. Corré las 20 preguntas de `03_Set_Preguntas_Prueba.md` y anotá resultados.
3. Verificaciones clave:
   - Pregunta 12 (SMED, números precisos): ¿cita el documento correcto?
   - Pregunta sobre el trabajo de 2009 (agregala: "¿qué scrap tenía la línea de pintura en 2009?"): si responde "8,5% → 2,1%", **el OCR funcionó**. Si no lo encuentra, revisá el parser del datastore histórico.
   - Preguntas 5/10/16/20 (canarias de alucinación): deben dar fallback honesto.
   - Pregunta 17 vs 18: ¿el enrutamiento por relevancia entre los dos datastores separa bien evento de histórico?

## Paso 9 — Publicar el widget

1. App → **Integration** → pestaña **Widget**.
2. Autorización: **Public Access** (recordá: posible solo porque la fuente es Cloud Storage sin ACL).
3. Agregá a la allowlist de dominios: `localhost`.
4. Copiá el snippet `<gen-search-widget>` en un HTML mínimo:
   ```html
   <!doctype html><html><body>
   <h1>Encuentro SAMECO 2026 — práctica</h1>
   <!-- pegá acá el snippet del widget -->
   </body></html>
   ```
5. Servilo local: `python3 -m http.server 8000` y abrí `http://localhost:8000`. Eso es exactamente lo que el webmaster de SAMECO pegará en el sitio real (allowlisteando su dominio).
6. Nota: el estilo del widget no es personalizable por CSS (limitación documentada) — bueno saberlo antes de que lo pregunten.

## Paso 10 — Simular la operación del equipo (el "día después")

Ensayá el procedimiento que vas a documentar para los no técnicos:
1. Subí un documento nuevo al bucket (p. ej. un DOCX "fe de erratas: la plenaria del viernes pasa a las 09:30").
2. Datastore → reimportá / esperá la sincronización.
3. Verificá en Preview que la respuesta a "¿a qué hora es la plenaria del viernes?" cambió.
4. Cronometrá cuánto tarda en reflejarse: ese número lo vas a necesitar cuando el equipo pregunte "¿cuándo aparece lo que subo?".

## Limpieza

Al terminar la práctica: IAM & Admin → Settings → **Shut down** el proyecto (borra todo, deja de facturar). Si querés conservarlo hasta el curso, el costo en reposo es solo el almacenamiento del índice (unos pocos GB = pocos dólares/mes) — con el crédito de prueba alcanza de sobra.

## Errores típicos viniendo de Azure (checklist de diagnóstico)

| Síntoma | Causa probable |
|---|---|
| 403 / PERMISSION_DENIED al crear algo | API no habilitada en el proyecto (no existe el "está todo disponible" de Azure) |
| No aparece la opción de respuestas generativas | Faltó el toggle de Advanced LLM features al crear la app |
| El escaneo no aparece en respuestas | Datastore creado con digital parser; recrealo con OCR/layout parser |
| Widget no carga en tu página | Dominio no allowlisteado, datastore con ACL, o cambios recientes sin propagar (**hasta 30 min**, lo dice la propia pantalla de Integration). Verificado ago-2026: con "Public Access" + `localhost` guardados, solo queda esperar. La página debe abrirse por `http://localhost:PUERTO`, nunca con doble clic (`file://` no es un dominio y no se puede allowlistear) |
| "Sync from Google Drive" falla | Cuenta personal sin Workspace (ver hallazgo crítico) |
| El documento nuevo no impacta | La reindexación no es instantánea; revisá Activity del datastore |
