# Instructivo E — Publicar el agente como chat web (Cloud Run)

**Requisito previo:** Instructivo B completado (agente creado en Agent Studio
con su herramienta de datastore funcionando en el Preview).

**Cuándo aplica:** cuando el canal elegido es **el agente** y no el widget de
la app de búsqueda. Los agentes de Agent Studio **no tienen widget embebible**
(verificado sept-2026): el botón Deploy publica una **API** (Agent Runtime),
y la interfaz de chat corre por cuenta de uno. Este instructivo publica esa
interfaz — un servidor web mínimo — en **Cloud Run**, con identidad de máquina
y sin secretos.

En el repo, las piezas viven en `curso/widget/`:

| Archivo | Qué es |
|---|---|
| `servidor_sameco.py` | El backend: sirve la página y expone `/api/chat`, replicando al agente (mismas instrucciones, mismo modelo, mismo datastore) |
| `index_sameco.html` | La página de chat (un solo panel) |
| `Dockerfile` | La imagen para Cloud Run, con el comando de deploy en el encabezado |

## La decisión de arquitectura: ¿local o remoto?

El servidor tiene dos modos, y elegir uno es una decisión de costos:

- **Modo local (default):** el servidor llama directo a Gemini con grounding
  sobre el datastore. Autocontenido: **no necesita la instancia de Agent
  Runtime**, que puede borrarse (deja de facturar por hora). Cloud Run escala
  a cero → sin tráfico, costo ≈ $0.
- **Modo remoto (`--remoto`):** el servidor le habla al agente deployado en
  Agent Runtime (sesiones server-side, el agente "oficial" de Agent Studio).
  Se paga Cloud Run **más** el Runtime por hora, exista tráfico o no.

Para un chat de evento, el modo local es el recomendado: mismo comportamiento
(las instrucciones y el datastore son idénticos), una pieza menos y factura
menor. El remoto queda para cuando el agente crezca (sub-agentes, más
herramientas, Memory Bank).

## La identidad: cuenta de servicio, sin claves

Regla de oro: **un servidor no se autentica con la cuenta de una persona**
(ata el servicio a un humano) **ni con claves JSON descargadas** (secreto de
larga vida que hay que custodiar — y las organizaciones nuevas de Google lo
bloquean de fábrica con la política `iam.disableServiceAccountKeyCreation`;
no pedir que la desactiven: es protección, no estorbo).

Lo correcto: una **cuenta de servicio adjunta al servicio de Cloud Run**. La
credencial nunca existe como archivo; Google se la inyecta al contenedor y la
librería (ADC) la encuentra sola, sin tocar el código. El servidor prende,
se apaga y vuelve a prender sin que nadie se loguee jamás.

1. **IAM y administración → Cuentas de servicio → Crear**: p. ej.
   `sami-servicio` → queda `sami-servicio@PROYECTO.iam.gserviceaccount.com`.
2. Asignarle exactamente dos roles (mínimo privilegio):
   - **Vertex AI User** — llamar a Gemini (y consultar el Runtime si se usa `--remoto`)
   - **Discovery Engine User** — buscar en el datastore

La misma cadena ADC resuelve la identidad según el entorno (equivalencia
Azure: `DefaultAzureCredential` + Managed Identity):

| Dónde corre | Identidad |
|---|---|
| Máquina del consultor (desarrollo) | Su usuario, vía `gcloud auth application-default login` (necesita esos 2 roles en el proyecto) |
| Cloud Run (producción) | La cuenta de servicio adjunta — automático, cero secretos |

## Publicar (10 minutos, desde Cloud Shell)

Cloud Shell es la terminal del navegador de la consola: ya corre autenticada
con la cuenta del proyecto, así que no hay que instalar ni loguear nada local.

1. Abrir **Cloud Shell** (ícono `>_` arriba a la derecha de la consola).
2. Subir los tres archivos de `curso/widget/` (menú ⋮ de Cloud Shell →
   Subir) o clonar el repo, y `cd` a la carpeta.
3. Deployar:

```bash
gcloud run deploy sami-chat \
  --source . \
  --project TU_PROYECTO \
  --region us-west1 \
  --service-account sami-servicio@TU_PROYECTO.iam.gserviceaccount.com \
  --allow-unauthenticated
```

4. La primera vez pide habilitar Cloud Build y Artifact Registry → aceptar.
   En unos minutos devuelve la URL pública: `https://sami-chat-….run.app`.
5. Probar desde otro dispositivo/red, no solo la propia máquina.

**En organizaciones "seguras por defecto" (como la de SAMECO), el primer
deploy necesita dos permisos más** — una sola vez, y los dos avisan con un
error claro si faltan (ver la tabla de abajo):

```bash
# 1) El "obrero" de Cloud Build (la SA default de Compute) nace sin permisos
#    ni para leer el código fuente subido. Su rol paquete:
gcloud projects add-iam-policy-binding TU_PROYECTO \
  --member="serviceAccount:NUMERO_DE_PROYECTO-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

# 2) Quien deploya necesita poder "actuar como" la SA del servicio:
gcloud iam service-accounts add-iam-policy-binding \
  sami-servicio@TU_PROYECTO.iam.gserviceaccount.com \
  --member="user:USUARIO_QUE_DEPLOYA" \
  --role="roles/iam.serviceAccountUser"
```

Detalles del código que ya están resueltos (por si se adapta a otro proyecto):
Cloud Run dicta el puerto por la variable `PORT` (el server la lee, con 8501
de fallback local) y el server usa `ThreadingHTTPServer` para atender
consultas en paralelo.

## Después de publicar: la lista corta

- **Alerta de presupuesto** en el proyecto (como en el Paso 2 del instructivo
  A): el chat es público y cada pregunta llama a Gemini — que un bot curioso
  no convierta la URL en una factura.
- **Exposición**: `--allow-unauthenticated` significa internet entera. Para el
  go-live conviene servirlo embebido/linkeado solo desde el sitio de la
  organización y considerar un límite de uso (rate limit) si el tráfico crece.
- **Si se eligió modo local**: borrar la instancia de Agent Runtime que quedó
  del Deploy de prueba (Implementaciones → ⋮ → Borrar), que factura por hora.
- **Correr el set de QA** (instructivo C) contra la URL publicada: es la
  evaluación formal del asistente en producción.

## Errores vistos en el camino (reales, sept-2026)

| Síntoma | Causa | Solución |
|---|---|---|
| `403 PERMISSION_DENIED … aiplatform.endpoints.predict` | La identidad ADC no tiene roles en el proyecto | Otorgar *Vertex AI User* + *Discovery Engine User* a esa cuenta (propaga en 1–10 min) |
| "La creación de claves de la cuenta de servicio está inhabilitada" | Política de la organización (`iam.disableServiceAccountKeyCreation`) | No pelearla: usar la SA **adjunta** a Cloud Run (este instructivo) |
| Deploy de Agent Runtime: "failed to start and cannot serve traffic" | Primer deploy en un proyecto recién creado (aprovisionamiento en curso) | Borrar la instancia fallida y reintentar; si repite, ver el traceback en Cloud Logging (`resource.type="aiplatform.googleapis.com/ReasoningEngine"`) |
| El server ignora el modo remoto | Flag mal tipeado | Es `--remoto` (el server acepta también `--remote`); al arrancar imprime el modo activo |
| Deploy: "Build failed because the default service account is missing required IAM permissions" / `permission_denied … -compute@developer.gserviceaccount.com` | En orgs seguras por defecto, la SA default de Compute (que usa Cloud Build) nace sin permisos | Rol **Cloud Build Service Account** (`roles/cloudbuild.builds.builder`) a `NUMERO-compute@developer.gserviceaccount.com` (comando en la sección de publicación) |
| Deploy: `PERMISSION_DENIED … iam.serviceaccounts.actAs` | Quien deploya no puede "actuar como" la SA del servicio | Rol **Service Account User** al usuario que deploya, sobre la SA `sami-servicio@…` |
| Build falla con "provide a main.py or app.py … or Procfile" | El deploy se corrió desde otra carpeta: sin `Dockerfile` a la vista, Cloud Build usa *buildpacks* y busca un entrypoint | Correr `gcloud run deploy --source .` **desde `curso/widget/`** (donde está el `Dockerfile`) |
| El servicio deployó pero la URL da 403; "Setting IAM policy failed" y el binding a `allUsers` rechaza con "does not belong to a permitted customer" | Política de la org de dominio restringido (`iam.allowedPolicyMemberDomains`): no se puede otorgar a `allUsers` | `gcloud run services update sami-chat --region us-west1 --no-invoker-iam-check` — la vía oficial de Cloud Run para servicios públicos en orgs restringidas, sin tocar políticas |
| Modo remoto: `'AgentEngine' object has no attribute 'create_session'` | La interfaz de `vertexai.agent_engines` cambia entre versiones del SDK | El server ya no usa ese SDK: llama la API REST de la instancia (`:streamQuery` con `class_method`) |
| Modo remoto sin memoria entre turnos (el agente repregunta "¿a qué te referís?") | `create_session` ya no es un método del agente (da 404); las sesiones son un recurso administrado | Crear la sesión con `POST …/reasoningEngines/ID/sessions` (`{"userId": …}`) y pasar su id como `session_id` en cada `stream_query` — ya resuelto en `servidor_sameco.py` (verificado sept-2026) |
