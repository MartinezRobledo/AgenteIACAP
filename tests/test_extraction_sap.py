import asyncio
import json
import logging
import requests
import hmac
import hashlib
import base64
import datetime
import os
from dotenv import load_dotenv
from urllib.parse import quote

from agentiacap.tools.busqueda_sap import SAP_buscar_por_factura, SAP_buscar_por_fecha_monto, SAP_buscar_por_fecha_base, procesar_solicitud_busqueda_sap

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

async def ExtractionSap(req: dict) -> dict:

    try:
        inputs = req["inputs"]
        urls_adjuntos = req["files"]

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

    try:
        for file in adjuntos:
            response = await procesar_solicitud_busqueda_sap(file, inputs)
    except Exception as e:
        logging.error(f"Error al invocar graph.ainvoke: {e}")
        return {"error": f"Error al procesar la solicitud. Error: {e}"}

    return response


# Obtiene la ruta absoluta del archivo 'caso.json' en relación con el script actual
script_dir = os.path.dirname(os.path.abspath(__file__))  # Directorio del script
file_path_input = os.path.join(script_dir, 'caso_sap.json')
file_path_output = os.path.join(script_dir, 'response_sap.json')

with open(file_path_input, 'r') as file:
    caso = json.load(file)

result = asyncio.run(ExtractionSap(caso))

with open(file_path_output, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=4)