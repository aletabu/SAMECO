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
# El servidor arranca en modo REMOTO: le habla al agente SAMI deployado en
# Agent Runtime (el cerebro vive en Agent Studio; el equipo lo edita ahí con
# Update, sin tocar este contenedor). Para el modo autocontenido sin Runtime
# (Gemini + datastore directo, sin costo por hora), quitar "--remoto" del CMD.

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir google-genai requests

COPY servidor_sameco.py index_sameco.html logo-sameco.png ./

CMD ["python", "servidor_sameco.py", "--remoto"]
