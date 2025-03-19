import logging
import requests
import azure.functions as func
import azure.durable_functions as df
import hmac
import hashlib
import base64
import datetime
import os
from dotenv import load_dotenv
from urllib.parse import quote

from agentiacap.utils.globals import InputSchema
from agentiacap.workflows.responser import responder_mail
from agentiacap.workflows.main import graph
from agentiacap.tools.op_data_extractor import ExtractSAP, ExtractEsker

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

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="orchestrators/{functionName}", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@app.durable_client_input(client_name="client")
async def AgenteIACAP(req: func.HttpRequest, client) -> func.HttpResponse:
    body = req.get_json()
    function_name = req.route_params.get('functionName')
    instance_id = await client.start_new(function_name, None, body)
    response = client.create_check_status_response(req, instance_id)
    return response

# Orchestrator: coordina la ejecución de la actividad
@app.orchestration_trigger(context_name="context")
def AgenteIACAP_Orchestrator(context: df.DurableOrchestrationContext):
    input_data = context.get_input()
    result = yield context.call_activity("AgenteIACAP_Activity", input_data)
    return result

@app.orchestration_trigger(context_name="context")
def Extraction_Orchestrator(context: df.DurableOrchestrationContext):
    input_data = context.get_input()
    # Obtener el nombre de la actividad desde el input
    activity_name = input_data.get("system")
    # Diccionario con las actividades disponibles
    activities = {
        "sap": ExtractionSap,
        "esker": ExtractionEsker,
    }
    
    if activity_name.lower() not in activities:
        raise ValueError(f"Actividad '{activity_name}' no encontrada.")
    
    # Llamar a la actividad correspondiente
    result = yield context.call_activity(activities[activity_name.lower()], input_data)
    return result

@app.orchestration_trigger(context_name="context")
def Responser_Orchestrator(context: df.DurableOrchestrationContext):
    input_data = context.get_input()
    
    # Llamar a la actividad
    result = yield context.call_activity(Responser, input_data)
    return result

# Activity: realiza el procesamiento (por ejemplo, invoca graph.ainvoke)
@app.activity_trigger(input_name="req")
async def AgenteIACAP_Activity(req: dict) -> dict:
    logging.info("Python HTTP trigger function processed a request.")

    try:
        asunto = req["asunto"]
        cuerpo = req["cuerpo"]
        urls_adjuntos = req["adjuntos"]  # Ahora recibimos URLs en lugar de IDs

    except Exception as e:
        return {"error": f"Body no válido. Error: {e}"}

    # Validar que 'adjuntos' sea una lista de URLs
    if not isinstance(urls_adjuntos, list):

        return {"error": "Los adjuntos deben ser una lista de URLs de archivos."}

    try:
        adjuntos = []
        for file_url in urls_adjuntos:
            archivo = obtener_blob_por_url(file_url)
            if archivo:
                adjuntos.append(archivo)
            else:
                logging.warning(f"No se pudo obtener el archivo desde {file_url}")
    except:
        return {"error": "Error al obtener archivos del storage."}
    
    # Preparar la entrada para la orquestación
    input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
    try:
        response = await graph.ainvoke(input=input_data)
    except Exception as e:
        logging.error(f"Error al invocar graph.ainvoke: {e}")
        return {"error": f"Error al procesar la solicitud. Error: {e}"}

    result = response.get("result", {})
    return result

@app.activity_trigger(input_name="req")
async def ExtractionSap(req: dict) -> dict:
    logging.info("Python activity function processed a request.")

    try:
        inputs = req["inputs"]
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

    try:
        response = await ExtractSAP(adjuntos, inputs)
    except Exception as e:
        logging.error(f"Error al invocar graph.ainvoke: {e}")
        return {"error": f"Error al procesar la solicitud. Error: {e}"}

    return response.get("extractions", {})

@app.activity_trigger(input_name="req")
async def ExtractionEsker(req: dict) -> dict:
    logging.info("Python activity function processed a request.")

    try:
        inputs = req["inputs"]
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

    try:
        response = await ExtractEsker(adjuntos, inputs)
    except Exception as e:
        logging.error(f"Error al invocar graph.ainvoke: {e}")
        return {"error": f"Error al procesar la solicitud. Error: {e}"}

    return response.get("aggregate", {})

@app.activity_trigger(input_name="req")
def Responser(req: dict) -> dict:
    logging.info("Python activity function processed a request.")

    try:
        inputs = req["inputs"]

    except Exception as e:
        return {"error": f"Body no válido. Error: {e}"}

    try:
        response = responder_mail(inputs)
    except Exception as e:
        logging.error(f"Error al invocar responser: {e}")
        return {"error": f"Error al procesar la solicitud. Error: {e}"}

    return response
