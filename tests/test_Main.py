import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import time
import pandas as pd
import requests
from agentiacap.utils.globals import InputSchema
from agentiacap.workflows.main import graph
import asyncio
from dotenv import load_dotenv
from urllib.parse import quote

from agentiacap.workflows.sentiment_validator import sentiment

INPUT_FILE = "D:\\Python\\Agentiacap\\Pruebas -12-03.xlsx"
OUTPUT_FILE = "D:\\Python\\Agentiacap\\Pruebas -12-03-Resultados.xlsx"

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
            logging.error(f"Error al descargar {blob_name}: {response.text}")
            raise

    except Exception as e:
        logging.error(f"Error al obtener archivo por URL: {e}")
        raise

async def process_excel():
    df = pd.read_excel(INPUT_FILE)
    
    if not {'body'}.issubset(df.columns):
        raise ValueError("El archivo Excel debe contener las columnas 'body'")
    
    if "Extracción Mail" not in df.columns:
        df["Extracción Mail"] = None
    if "Extracción D.I." not in df.columns:
        df["Extracción D.I."] = None
    if "Extracción Vision" not in df.columns:
        df["Extracción Vision"] = None
    if "Categoria inferida" not in df.columns:
        df["Categoria inferida"] = None
    if "Sentimiento" not in df.columns:
        df["Sentimiento"] = None
    if "Resume" not in df.columns:
        df["Resume"] = None
    if "Message" not in df.columns:
        df["Message"] = None
    
    for index, row in df.iterrows():
        try:
            urls_adjuntos = json.loads(row["body"])["adjuntos"]
            cuerpo = json.loads(row["body"])["cuerpo"]
            asunto = json.loads(row["body"])["asunto"]
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
            
            # for path in [adjuntos_path, adjuntos_path_id]:
            #     if os.path.exists(path):
            #         for file_path in glob.glob(os.path.join(path, '*')):
            #             with open(file_path, "rb") as file:
            #                 encoded_string = base64.b64encode(file.read()).decode("utf-8")
            #                 adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})
            
            input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
            response = await graph.ainvoke(input=input_data)
            result = response.get("result", {})
            category = result.get("category", {})
            resume = result.get("resume", {})
            message = result.get("message", {})
            print(f"DEBUG - Categoria obtenida: {category}")
            extractions = result.get("extractions", {})
            df.at[index, "Categoria inferida"] = category if category else "No detectada"
            response = await sentiment(subject=asunto, message=cuerpo)    
            try:
                if isinstance(extractions, list):
                    extractions = json.dumps(extractions)
                data = json.loads(extractions)
                # Diccionario para almacenar datos agrupados por "Fuente"
                fuentes = {"Mail": [], "Document Intelligence": [], "Vision": []}
                # Procesar los datos y agrupar por fuente
                for item in data:
                    fuente = item["source"]
                    if fuente in fuentes:
                        fuentes[fuente].extend(item["extractions"])

                # Variables separadas por fuente
                fuente_Mail = fuentes["Mail"]
                fuente_Document_Intelligence = fuentes["Document Intelligence"]
                fuente_Vision = fuentes["Vision"]
                df.at[index, "Extracción Mail"] = fuente_Mail
                df.at[index, "Extracción D.I."] = fuente_Document_Intelligence
                df.at[index, "Extracción Vision"] = fuente_Vision
                df.at[index, "Sentimiento"] = response
                df.at[index, "Resume"] = resume
                df.at[index, "Message"] = message
            except json.JSONDecodeError:
                df.at[index, "Extracción Mail"] = "Error JSON"
                df.at[index, "Extracción D.I."] = "Error JSON"
                df.at[index, "Extracción Vision"] = "Error JSON"
                    
            
            df.to_excel(OUTPUT_FILE, index=False)
            print(f"Fila {index} procesada y guardada en Excel.")
            time.sleep(1)
        except Exception as e:
            print(f"Error en fila {index}: {e}")
            df.at[index, "Extracción Mail"] = "Error"
            df.at[index, "Extracción D.I."] = "Error"
            df.at[index, "Extracción Vision"] = "Error"
            df.at[index, "Categoria inferida"] = "Error"
            df.at[index, "Time"] = 0
            df.to_excel(OUTPUT_FILE, index=False)
            time.sleep(2)


import os
async def process_json():

    # Obtiene la ruta absoluta del archivo 'caso.json' en relación con el script actual
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directorio del script
    file_path_input = os.path.join(script_dir, 'caso.json')
    file_path_output = os.path.join(script_dir, 'response.json')

    with open(file_path_input, 'r') as file:
        content = json.load(file)

    asunto = content.get('asunto')
    cuerpo = content.get('cuerpo')
    urls_adjuntos = content.get('adjuntos')

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
    try:
        input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
        response = await graph.ainvoke(input=input_data)
        result = response.get("result", {})
        with open(file_path_output, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)


if __name__ == "__main__":
    # asyncio.run(process_excel())
    asyncio.run(process_json())
