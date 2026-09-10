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
# El servidor arranca en modo local (Gemini + datastore directo, sin depender
# del Agent Runtime). Para que use la instancia deployada de SAMI, cambiar el
# CMD a ["python", "servidor_sameco.py", "--remoto"].

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir google-genai "google-cloud-aiplatform[agent_engines]"

COPY servidor_sameco.py index_sameco.html logo-sameco.png ./

CMD ["python", "servidor_sameco.py"]
