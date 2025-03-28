import base64
import datetime
import hashlib
import hmac
import logging
import os
from urllib.parse import quote
from dotenv import load_dotenv
import requests

from agentiacap.tools.documents_classifier import wrapper_es_carta_modelo


#Cargar las variables de entorno desde el archivo .env
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

        blob_name_encoded = quote(blob_name, safe="/")
        date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        blob_url = f"{STORAGE_ACCOUNT_ENDPOINT}/{STORAGE_ACCOUNT_CONTAINER_NAME}/{blob_name_encoded}"
        canonicalized_resource = f"/{STORAGE_ACCOUNT_NAME}/{STORAGE_ACCOUNT_CONTAINER_NAME}/{blob_name_encoded}"

        headers = {
            "x-ms-date": date,
            "x-ms-version": "2021-12-02",
            "Authorization": generar_firma_azure("GET", "", "", date, canonicalized_resource)
        }

        response = requests.get(blob_url, headers=headers)

        if response.status_code == 200:
            return {"file_name": blob_name, "content": response.content}
        else:
            error_msg = f"Error al descargar {blob_name}: {response.text}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    except Exception as e:
        logging.error(f"Error al obtener archivo por URL: {e}")
        raise

def wrapper_carta_modelo(req):
    logging.info("Python activity function processed a request.")

    try:
        urls_adjuntos = req["adjuntos"]

    except Exception as e:
        return {"error": f"Body no válido. Error: {e}"}

    # Validar que 'adjuntos' sea una lista de URLs
    if not isinstance(urls_adjuntos, list):
        return {
            "error": "Los adjuntos deben ser una lista de URLs de archivos."
        }

    try:
        adjuntos = []
        for file_url in urls_adjuntos:
            archivo = obtener_blob_por_url(file_url)
            if archivo:
                adjuntos.append(archivo)
            else:
                logging.warning(f"No se pudo obtener el archivo desde {file_url}")
    except Exception as e:
        return {"error": f"Error al obtener archivos del storage. Error: {e}"}
    
    response = wrapper_es_carta_modelo({"pdfs":adjuntos})
    return response

result = wrapper_carta_modelo({"adjuntos": [
        {
            "file_name": "Ejemplo carta modelo.pdf"
        },
        {
            "file_name": "Test/30707248757-00008A00014432.pdf"
        },
        {
            "file_name": "Test/Nota modelo-Devolución de Retenciones2000091532.pdf"
        }
    ]})

print(result)