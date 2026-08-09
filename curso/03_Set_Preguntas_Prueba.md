# Set de preguntas de prueba (para tu sandbox y para el curso)

La guía de capacitación recomienda un set fijo de 15–20 preguntas para comparar versiones del prompt de forma pareja. Este set está armado contra el material de práctica de `material_practica/`. Cada pregunta tiene la respuesta esperada y qué capacidad valida. En SAMECO se replica el mismo esquema con sus documentos reales.

## Bloque A — Evento (datastore "Evento Octubre 2026")

| # | Pregunta | Respuesta esperada | Valida |
|---|---|---|---|
| 1 | ¿Qué días es el encuentro? | Jueves 22 y viernes 23 de octubre de 2026 | Recuperación básica |
| 2 | ¿A qué hora abren las puertas? | 08:00 ambos días | Dato puntual "escondido" al pie de la agenda |
| 3 | ¿Quién da la charla de apertura y de qué trata? | Ing. Marta Villanueva, "La mejora continua en la era de la IA" (10:00, Auditorio A) | Cruce agenda ↔ oradores |
| 4 | ¿Cuánto sale la inscripción para estudiantes? | $20.000 early bird / $25.000 después del 15/09 | Lectura de tabla con condición temporal |
| 5 | ¿La inscripción incluye el almuerzo? | No; incluye coffee breaks, material y certificado | Negación explícita (trampa típica de alucinación) |
| 6 | ¿Cómo llego en subte? | Línea B, estación Carlos Pellegrini | Recuperación básica |
| 7 | ¿El taller de A3 requiere algo especial? | Cupo de 40, inscripción previa en acreditación | Dato condicional |
| 8 | ¿Y el segundo día a la mañana qué hay? | Plenaria de S. Ferreyra 09:00 + tanda 3 de trabajos | **Pregunta de seguimiento** (contexto conversacional) |
| 9 | ¿Hay descuento de hotel? | 15% en Hotel Presidente, código ENCUENTRO2026, hasta 30/09 | Recuperación con código exacto |
| 10 | ¿Va a estar Carlos Pagni en el evento? | No figura en el material → "no cuento con ese dato" | **Fallback / no inventar** |

## Bloque B — Histórico (datastore "Trabajos históricos")

| # | Pregunta | Respuesta esperada | Valida |
|---|---|---|---|
| 11 | ¿Hay trabajos sobre 5S? | Sí, el de la metalúrgica de Villa Constitución (2018) | Búsqueda temática |
| 12 | ¿Qué resultados logró el trabajo de SMED? | De 94 a 31 minutos (67%), +2,1 h/día, repago < 4 meses | Datos numéricos precisos |
| 13 | ¿Se aplicó mejora continua en salud alguna vez? | Sí: kaizen en guardia hospitalaria (2023), espera de 4:20 a 2:05 | Búsqueda temática + síntesis |
| 14 | ¿Quiénes escribieron el trabajo de 5S y de qué año es? | J. Domínguez y R. Salas, 2018 | Metadatos de autoría |
| 15 | ¿Cuál fue el factor de éxito común en los trabajos presentados? | Síntesis: compromiso de supervisión, participación de operarios, equipos mixtos | **Síntesis multi-documento** |
| 16 | ¿Hay algún trabajo sobre Six Sigma en bancos? | No hay → fallback honesto | No inventar en dominio histórico |

## Bloque C — Enrutamiento entre dominios (el punto fino del diseño 1 agente + 2 datastores)

| # | Pregunta | Comportamiento esperado |
|---|---|---|
| 17 | "¿Dónde es el evento?" | Responde SOLO con material del evento, sin mezclar histórico |
| 18 | "¿Qué se presentó sobre kaizen en años anteriores?" | Va al histórico, cita el trabajo de 2023 |
| 19 | "¿En el evento de octubre va a haber charlas de kaizen como las de antes?" | Pregunta mixta: idealmente cita agenda 2026 **y** referencia histórica, sin confundir fechas |
| 20 | "¿Cuánto salía la inscripción en 2018?" | El material histórico no tiene aranceles → fallback, sin usar los precios de 2026 | 

## Cómo usarlo

1. Pasá las 20 preguntas con la **misma versión del prompt** y anotá: correcta / incompleta / inventada / fallback correcto.
2. Ajustá **una sola instrucción** del prompt por iteración y volvé a correr el set completo.
3. Las preguntas 5, 10, 16 y 20 son las canarias de alucinación: si alguna falla, el grounding no está bien ajustado — es lo primero que hay que arreglar antes de seguir.
4. Guardá una planilla con columnas: fecha, versión de prompt, resultado por pregunta. Esa planilla es también material didáctico para la Sesión 3 con el equipo.
