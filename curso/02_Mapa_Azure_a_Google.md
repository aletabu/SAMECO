# Mapa de conceptos: Azure → Google Cloud

Traducción directa para vos, Alejandro: cada pieza que ya conocés de Azure y su equivalente en el stack de Google que vas a usar en SAMECO. La columna "rol en SAMECO" indica qué papel juega en el proyecto concreto.

| Azure (lo que conocés) | Google Cloud (lo que vas a usar) | Rol en SAMECO |
|---|---|---|
| Azure Portal | Google Cloud Console (`console.cloud.google.com`) | Consola única de administración |
| Suscripción + Resource Group | **Proyecto** de GCP (no hay resource groups: el proyecto es la unidad de todo — facturación, permisos, APIs) | Un proyecto para el sandbox, otro (o el mismo) para SAMECO |
| Azure AI Search (Cognitive Search) + integración "On Your Data" de Azure OpenAI | **Vertex AI Search / AI Applications** (motor: Discovery Engine). El *data store* es índice + pipeline de ingesta en uno | Los 2 datastores: "Evento" e "Histórico" |
| Indexer + Skillset de AI Search (chunking, OCR skill, embeddings) | Lo hace el data store automáticamente al importar (parsing, chunking, embeddings, OCR según configuración) | Por eso la propuesta es "gestionada": no armás pipeline |
| Azure OpenAI Service (deployment de modelos) | **Vertex AI** (los modelos Gemini ya están disponibles, no hay que "deployar"; Claude y otros vía Model Garden) | El LLM que redacta las respuestas (Gemini Flash) |
| Azure AI Document Intelligence (Form Recognizer) | **Document AI** (processor de OCR) | OCR de escaneos antiguos del archivo histórico |
| Blob Storage (contenedor) | **Cloud Storage** (bucket) | Donde suben PDFs para ingestar al datastore |
| SharePoint/OneDrive como fuente del indexer | **Conector de Google Drive** del data store | La "biblioteca" que mantiene el equipo no técnico |
| Copilot Studio / Azure Bot Service (canalizar el bot) | Widget web embebible de la app de búsqueda, o **Gemini Enterprise** (portal por usuario) | Widget = web pública; portal = las 4 personas internas |
| System prompt / system message en Azure OpenAI | Instrucciones del agente / "system instructions" en la app | El prompt del asistente (rol, tono, grounding) |
| Grounding con "On Your Data" (cita de fuentes) | Grounding nativo del data store con **citations** | La regla "si no está en los documentos, no lo inventes" |
| Entra ID (RBAC: Owner/Contributor/Reader) | **IAM** de GCP (roles: Owner/Editor/Viewer + roles finos como `discoveryengine.admin`) | Permisos del equipo sobre el proyecto |
| `az` CLI | `gcloud` CLI | Scripts reproducibles (Parte B de la guía técnica) |
| Cost Management + Budgets | **Billing** + Budgets & alerts | Poner alerta de presupuesto el día 1 del sandbox |
| text-embedding-ada / text-embedding-3 | Familia **gemini-embedding / text-embedding** de Vertex | Solo para la demo "por dentro"; el datastore lo hace solo |
| Prompt flow / AI Foundry playground | Panel **Preview** de la app + Vertex AI Studio | Donde probás el set de preguntas reales |

## Diferencias que te van a sorprender viniendo de Azure

1. **No hay "deployment" de modelos.** En Azure OpenAI creás un deployment por modelo; en Vertex los modelos Gemini están disponibles directamente por API/consola apenas habilitás la API. Menos pasos, menos control de versión pinneada (elegís el modelo por nombre en cada llamada/configuración).
2. **El proyecto lo es todo.** Sin resource groups ni suscripciones anidadas: APIs se habilitan por proyecto, la facturación se asocia por proyecto, IAM se hereda de organización → carpeta → proyecto. Para el sandbox: un proyecto nuevo y limpio, y al terminar lo cerrás (shut down) y desaparece todo.
3. **Habilitar APIs es un paso explícito.** En Azure casi todo está "disponible"; en GCP cada servicio (Discovery Engine, Document AI, Vertex AI) hay que habilitarlo en el proyecto la primera vez. Si algo da error 403 al empezar, en el 90% de los casos es una API sin habilitar.
4. **El data store es más "todo en uno" que Azure AI Search.** No definís índice, skillset ni campos: elegís la fuente (bucket, Drive, website), el tipo de parsing, y Google resuelve chunking y embeddings. Ganás simplicidad, perdés control fino (no elegís chunk size en el modo básico — existe configuración de chunking para "layout parser" si hiciera falta).
5. **Citas de fuente vienen de fábrica.** Lo que en Azure armabas con "On Your Data" + referencias, acá es una opción del summary/answer de la app.
6. **Los nombres comerciales rotan rápido.** Agent Builder → AI Applications → Gemini Enterprise… el motor subyacente (Discovery Engine API) es estable; guiate por las APIs, no por el marketing. En el curso conviene decirle al equipo el nombre que se ve HOY en la consola y avisar que puede cambiar.
