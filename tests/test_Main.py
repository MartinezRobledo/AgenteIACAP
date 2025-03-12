import asyncio
import base64
import json
import os
import glob
import time
import pandas as pd
from agentiacap.utils.globals import InputSchema
from agentiacap.workflows.main import graph

INPUT_FILE = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Pruebas - 02-06.xlsx"
OUTPUT_FILE = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Casos - Extracción - Resultados.xlsx"


async def process_excel():
    df = pd.read_excel(INPUT_FILE)
    
    if not {'Asunto', 'Cuerpo', 'IDCaso', "ID"}.issubset(df.columns):
        raise ValueError("El archivo Excel debe contener las columnas 'Asunto', 'Cuerpo', 'IDCaso' e 'ID'")
    
    if "Extracción Mail" not in df.columns:
        df["Extracción Mail"] = None
    if "Extracción D.I." not in df.columns:
        df["Extracción D.I."] = None
    if "Extracción Vision" not in df.columns:
        df["Extracción Vision"] = None
    if "Categoria inferida" not in df.columns:
        df["Categoria inferida"] = None
    if "Time" not in df.columns:
        df["Time"] = None
    if "Tokens" not in df.columns:
        df["Tokens"] = None
    
    for index, row in df.iterrows():
        try:
            start_time = time.perf_counter()
            case_id = row['IDCaso']
            id = row['ID']
            adjuntos_list = []
            adjuntos_path = f"C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Adjuntos\\{case_id}"
            adjuntos_path_id = f"C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Adjuntos\\{id}"
            
            for path in [adjuntos_path, adjuntos_path_id]:
                if os.path.exists(path):
                    for file_path in glob.glob(os.path.join(path, '*')):
                        with open(file_path, "rb") as file:
                            encoded_string = base64.b64encode(file.read()).decode("utf-8")
                            adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})
            
            input_data = InputSchema(asunto=row['Asunto'], cuerpo=row['Cuerpo'], adjuntos=adjuntos_list)
            response = await graph.ainvoke(input=input_data)
            result = response.get("result", {})
            category = result.get("category", {})
            print(f"DEBUG - Categoria obtenida: {category}")
            extractions = result.get("extractions", {})
            tokens = result.get("tokens", {})
            print(f"DEBUG - Total de tokens: {tokens}")
            df.at[index, "Categoria inferida"] = category if category else "No detectada"
            df.at[index, "Tokens"] = tokens if tokens else "Null"
                
            try:
                if isinstance(extractions, list):
                    extractions = json.dumps(extractions)
                data = json.loads(extractions)
                # Diccionario para almacenar datos agrupados por "Fuente"
                fuentes = {"Mail": [], "Document Intelligence": [], "Vision": []}
                # Procesar los datos y agrupar por fuente
                for item in data:
                    fuente = item["fuente"]
                    if fuente in fuentes:
                        fuentes[fuente].extend(item["valores"])

                # Variables separadas por fuente
                fuente_Mail = fuentes["Mail"]
                fuente_Document_Intelligence = fuentes["Document Intelligence"]
                fuente_Vision = fuentes["Vision"]
                df.at[index, "Extracción Mail"] = fuente_Mail
                df.at[index, "Extracción D.I."] = fuente_Document_Intelligence
                df.at[index, "Extracción Vision"] = fuente_Vision
            except json.JSONDecodeError:
                df.at[index, "Extracción Mail"] = "Error JSON"
                df.at[index, "Extracción D.I."] = "Error JSON"
                df.at[index, "Extracción Vision"] = "Error JSON"
                    
            
            elapsed_time = time.perf_counter() - start_time
            df.at[index, "Time"] = elapsed_time
            
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
    file_path = os.path.join(script_dir, 'caso.json')

    with open(file_path, 'r') as file:
        content = json.load(file)

    asunto = content.get('asunto')
    cuerpo = content.get('cuerpo')
    adjuntos_list = content.get('adjuntos')
    try:
        input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos_list)
        response = await graph.ainvoke(input=input_data)
        result = response.get("result", {})
        print("DEBUG-Result: ", result)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)


if __name__ == "__main__":
    # asyncio.run(process_excel())
    asyncio.run(process_json())
