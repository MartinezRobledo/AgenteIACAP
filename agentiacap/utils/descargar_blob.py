import base64
import datetime
import hashlib
import hmac
import logging
import os
from urllib.parse import quote
from dotenv import load_dotenv
import requests


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

def obtener_blob_azure(blob:str):
    """
    Descarga un archivo desde Azure Blob Storage utilizando su nombre y autenticación con Access Key.

    Esta función genera una firma de autenticación compatible con Azure Blob Storage (Shared Key)
    para realizar una solicitud HTTP GET y recuperar el contenido binario del blob solicitado.

    Args:
        blob (str): Nombre del blob dentro del contenedor (puede incluir rutas, por ejemplo: "carpeta/archivo.pdf").

    Returns:
        dict: Un diccionario con:
            - "file_name": el nombre del archivo solicitado.
            - "content": contenido binario del blob (archivo descargado).

    Raises:
        RuntimeError: Si la descarga falla por error de autenticación o archivo inexistente.
        Exception: Para cualquier otro error inesperado durante la operación.
    """
    try:
        print("Descargando blob...")
        blob_name_encoded = quote(blob, safe="/")
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
            return {"file_name": blob, "content": response.content}
        else:
            error_msg = f"Error al descargar {blob}: {response.text}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    except Exception as e:
        logging.error(f"Error al obtener archivo por URL: {e}")
        raise