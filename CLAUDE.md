# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

No es un repositorio de código: son los materiales de una asesoría de Alejandro a SAMECO para dejar productivo un asistente Q&A (1 agente + 2 datastores: "Evento octubre 2026" + "Archivo histórico") sobre Google Cloud (Agent Search / AI Applications), con un curso de 4 sesiones de 1,5 h para un equipo no técnico de ~4 personas. Todo el contenido está en español rioplatense (voseo: "hacés", "tené") — mantener ese registro al editar o crear material.

## Estructura

- **Raíz (`.docx`)**: entregables formales para el cliente (propuesta, guías técnica y de capacitación). `Propuesta_Asesoria_Agente_QA_v2.docx` es el contrato de alcance. **Solo locales, fuera del repo** (gitignoreados): su contenido fue absorbido por `curso/instructivos/`, salvo la mini-demo RAG en Python (Parte B.5 de la guía técnica) y la propuesta misma.
- **`curso/*.md`**: materiales de preparación de Alejandro, numerados 00–04. `00_Plan_del_Curso.md` es el índice maestro: mapea cada sesión con su documento de respaldo y lista los riesgos vigentes.
- **`curso/material_practica/`**: documentos ficticios para el sandbox, en pares `.md` (fuente) + `.docx` (generado con `python-docx`). Subcarpetas `evento/` e `historico/`; incluye `trabajo_2009_escaneado_pintura.pdf`, un escaneo simulado (imagen sin capa de texto) para demos de OCR — no "arreglarlo" agregándole texto seleccionable.

Al editar material de práctica: el `.md` es la fuente; regenerar el `.docx` correspondiente para que no diverjan. El set de preguntas de `03_Set_Preguntas_Prueba.md` está calibrado contra datos concretos del material de práctica (fechas, precios, nombres) — si se cambia un dato en el material, revisar que las respuestas esperadas del set sigan siendo correctas, y viceversa.

## Nombres de producto y cifras (crítico)

Google renombra estos productos seguido. La referencia canónica es `curso/04_Actualizacion_2026_Nombres_y_Costos.md` (verificado ago-2026): docs = **"Agent Search"**, consola = **"AI Applications"** (`console.cloud.google.com/gen-app-builder/`), API = **Discovery Engine** (estable). No usar "Vertex AI Search" ni "Agent Builder" en material nuevo salvo como aclaración histórica. Cualquier cifra de precios o nombre nuevo debe verificarse contra páginas oficiales de Google Cloud y fecharse ("verificado <mes-año>") antes de incorporarse a los materiales.

## Decisiones de diseño ya tomadas (no reabrir)

- 1 agente + 2 datastores (no dos agentes); el diseño se explica con la analogía de la biblioteca (datastore = biblioteca, agente = bibliotecario que cita sus fuentes).
- SAMECO **sí tiene Google Workspace** (confirmado ago-2026): Drive es viable para el datastore interno, pero el widget público del evento debe alimentarse desde **Cloud Storage** (los datastores de Drive tienen ACL y no admiten "Public Access").
- El sandbox de práctica de Alejandro usa cuenta personal → todo por Cloud Storage (el conector de Drive no funciona con @gmail.com).
- Regla didáctica: cero código en pantalla salvo la demo opcional de la Sesión 4; el material del curso se escribe para audiencia no técnica.
- El caché de respuestas es optimización post-evento; no prometerlo para el go-live.
