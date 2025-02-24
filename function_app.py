import asyncio
import logging
import json
import requests
import azure.functions as func
import hmac
import hashlib
import base64
import datetime
import os
from dotenv import load_dotenv

from agentiacap.utils.globals import InputSchema
from agentiacap.workflows.main import graph

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

STORAGE_ACCOUNT_KEY = os.getenv("STORAGE_ACCOUNT_KEY")
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
STORAGE_ACCOUNT_CONTAINER_NAME = os.getenv("STORAGE_ACCOUNT_CONTAINER_NAME")
STORAGE_ACCOUNT_ENDPOINT = os.getenv("STORAGE_ACCOUNT_ENDPOINT")

def generar_firma_azure(verb, content_length, content_type, date, canonicalized_resource):
    """Genera la firma para la autenticación con la Access Key"""
    string_to_sign = f"{verb}\n\n\n{content_length}\n\n{content_type}\n\n\n\n\n\n\nx-ms-date:{date}\nx-ms-version:2021-12-02\n{canonicalized_resource}"
    key = base64.b64decode(STORAGE_ACCOUNT_KEY)
    signature = base64.b64encode(hmac.new(key, string_to_sign.encode('utf-8'), hashlib.sha256).digest()).decode()
    return f"SharedKey {STORAGE_ACCOUNT_NAME}:{signature}"

def obtener_blob_por_url(blob: dict):
    """Descarga un archivo desde Azure Blob Storage usando su URL autenticada con Access Key."""
    try:
        if isinstance(blob, dict):  # Verificar si 'file_url' es un diccionario
            blob_name = blob.get("file_name", "")

        date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        blob_url = f"{STORAGE_ACCOUNT_ENDPOINT}/{STORAGE_ACCOUNT_CONTAINER_NAME}/{blob_name}"
        canonicalized_resource = f"/{STORAGE_ACCOUNT_NAME}/{STORAGE_ACCOUNT_CONTAINER_NAME}/{blob_name}"

        headers = {
            "x-ms-date": date,
            "x-ms-version": "2021-12-02",
            "Authorization": generar_firma_azure("GET", "", "", date, canonicalized_resource)
        }

        response = requests.get(blob_url, headers=headers)

        if response.status_code == 200:
            return {"file_name": blob_name, "content": response.content}
        else:
            logging.error(f"Error al descargar {blob_name}: {response.text}")
            raise

    except Exception as e:
        logging.error(f"Error al obtener archivo por URL: {e}")
        raise
    
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="AgenteIACAP", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def AgenteIACAP(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    loop = asyncio.get_running_loop()
    loop.set_task_factory(None)

    # listar_blobs()
    try:
        body = req.get_json()
        asunto = body.get("asunto")
        cuerpo = body.get("cuerpo")
        urls_adjuntos = body.get("adjuntos")  # Ahora recibimos URLs en lugar de IDs

    except Exception as e:
        return func.HttpResponse(f"Body no válido. Error: {e}", status_code=400)

    # Validar que 'adjuntos' sea una lista de URLs
    if not isinstance(urls_adjuntos, list):
        return func.HttpResponse(
            json.dumps({"error": "Los adjuntos deben ser una lista de URLs de archivos."}),
            mimetype="application/json",
            status_code=400
        )

    try:
        adjuntos = []
        for file_url in urls_adjuntos:
            archivo = obtener_blob_por_url(file_url)
            if archivo:
                adjuntos.append(archivo)
            else:
                logging.warning(f"No se pudo obtener el archivo desde {file_url}")
    except:
        return func.HttpResponse("Error al obtener archivos del storage.", status_code=500)

    # Crear el objeto de entrada para el flujo
    input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)

    try:
        response = await graph.ainvoke(input=input_data)
    except Exception as e:
        logging.error(f"❌ Error al invocar graph.ainvoke: {e}")
        return func.HttpResponse("Error al procesar la solicitud.", status_code=500)

    result = response.get("result", {})

    return func.HttpResponse(
        json.dumps(result, indent=2),
        mimetype="application/json",
        status_code=200
    )