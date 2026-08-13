# Instructivo C — QA: el set de pruebas y su corrida automática

Un asistente RAG no se evalúa "probando un par de preguntas": se evalúa con un
**set fijo** que se corre completo cada vez que algo cambia (una instrucción,
un documento). Este instructivo trae la metodología y un corredor automático
que llama a la app por API y hace el triage de resultados con un modelo juez.

**Requisito previo:** Instructivo A completado (app funcionando).

## 1. El set: 4 tipos de pregunta, respuestas esperadas

Armá 15–20 preguntas fijas con su respuesta esperada, cubriendo los 4 tipos:

| Tipo | Qué valida | Ejemplo |
|---|---|---|
| **Factual** | Recuperación de un dato puntual (incluye trampas: negaciones explícitas, códigos, tablas con condición) | "¿Cuánto sale la inscripción para estudiantes?" |
| **Síntesis** | Combinar varios documentos en una respuesta | "¿Qué factor de éxito se repite en los trabajos?" |
| **Canaria** 🐤 | La respuesta correcta es "no lo sé" — detectan alucinación | "¿Va a estar Carlos Pagni?" |
| **Seguimiento / ambigua** | El contexto conversacional | "¿y el segundo día a la mañana?" |

Plantilla lista en `curso/scripts/set_pruebas.json` (21 preguntas contra el
material de práctica; para tu caso real, reemplazá preguntas y esperados).

**Regla de las canarias:** si una canaria falla (inventó en vez de admitir),
el grounding está mal y se arregla ANTES que cualquier otra cosa.

## 2. La escala de anotación

Cada respuesta se clasifica en: **correcta** · **incompleta** · **inventada**
(la peor) · **fallback correcto** (canaria que admitió no saber) ·
**fallback incorrecto** (dijo "no sé" cuando SÍ tenía el dato). La planilla
acumulada (fecha, versión de instrucciones, veredicto por pregunta) es la
memoria de calidad del asistente.

## 3. La corrida automática

`curso/scripts/correr_set_pruebas.py` hace todo el ciclo:

1. Llama a la **Answer API** del engine (la misma app del widget) por cada
   pregunta — con **sesión encadenada** para las de seguimiento (campo
   `sigue_a` del JSON).
2. Le pide a **Gemini (juez)** un veredicto contra la respuesta esperada, con
   salida estructurada.
3. Escribe `resultados_<fecha>.csv` y muestra el resumen con las canarias
   falladas y lo que hay que revisar a mano.

```bash
pip3 install --user google-genai requests
gcloud auth application-default login   # una vez
# editar PROJECT / ENGINE en el script
python3 correr_set_pruebas.py
```

Salida real de ejemplo (sandbox SAMECO, ago-2026): `16/21 correctas` en la
primera corrida, con la síntesis multi-documento y una respuesta de OCR
incompleta como hallazgos genuinos a iterar.

## 4. Cómo leer los resultados (importante)

El juez automático es **triage, no sentencia**:

- Las `correcta` y los `fallback_correcto` de canarias son confiables.
- Las `inventada` e `incompleta` se **revisan a mano** contra el documento
  fuente antes de actuar: el juez solo conoce la "respuesta esperada", no el
  documento — si el asistente agrega información verdadera que la esperada no
  menciona, puede marcar falso positivo.
- El set también se equivoca: si una pregunta está mal etiquetada (p. ej. una
  "canaria" cuya respuesta sí está en los documentos), corregí el set, no el
  asistente.

## 5. El ciclo de iteración

1. Corré el set completo → planilla.
2. Elegí LA peor falla (prioridad: canarias > inventadas > incompletas).
3. Cambiá **una sola cosa**: una instrucción del prompt o un documento fuente.
4. Volvé a correr el set **completo** (no solo la pregunta arreglada — un
   cambio puede romper otra cosa).
5. Compará contra la corrida anterior. Repetí.

> Regla de oro: si cambiás dos cosas y mejora, no sabés cuál fue.

## Costos de la corrida

Cada corrida son ~21 llamadas a la Answer API (cubiertas por el free tier de
10.000 consultas/mes; las respuestas generativas avanzadas se facturan aparte,
~$0,10 por corrida completa) + ~21 llamadas al juez Flash (centavos).
Correlo con confianza: es la herramienta de calidad más barata del proyecto.
