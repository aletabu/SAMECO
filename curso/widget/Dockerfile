# Imagen del chat SAMI para Cloud Run (proyecto agente-biblioteca).
# La autenticación NO va acá: Cloud Run le adjunta la cuenta de servicio
# (sami-servicio@agente-biblioteca.iam.gserviceaccount.com) y ADC la usa sola.
#
# Deploy (desde esta carpeta, con la cuenta SAMECO en gcloud o en Cloud Shell):
#   gcloud run deploy sami-chat \
#     --source . \
#     --project agente-biblioteca \
#     --region us-west1 \
#     --service-account sami-servicio@agente-biblioteca.iam.gserviceaccount.com \
#     --allow-unauthenticated
#
# El servidor arranca en modo LOCAL (autocontenido): Gemini + datastore
# directo, sin instancia de Agent Runtime → sin costo fijo por hora; las
# instrucciones de SAMI viven en servidor_sameco.py. Para volver al agente
# hosteado (edición de prompt con clics en Agent Studio): re-deployar SAMI
# desde el Designer, actualizar AGENT_ENGINE con el ID nuevo y agregar
# "--remoto" al CMD.

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir google-genai requests

COPY servidor_sameco.py index_sameco.html logo-sameco.png ./

CMD ["python", "servidor_sameco.py"]
