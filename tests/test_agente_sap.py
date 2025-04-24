import asyncio
import json
import logging
import os
from agentiacap.agents.agente_sap import agente_sap
from langchain_core.messages import HumanMessage

def ExtractionSap(req: dict) -> dict:
    logging.info("Python activity function processed a request.")

    try:
        inputs = req["inputs"]
        blobs = req["files"]

    except Exception as e:
        return {"error": f"Body no válido. Error: {e}"}

    # Validar que 'adjuntos' sea una lista de URLs
    if not isinstance(blobs, list):
        return {
            "error": "Los adjuntos deben ser una lista de URLs de archivos."
        }

    try:
        initial_state = {
            "messages": [
                HumanMessage(content="Hola, por favor procesá estos datos.")
            ],
            "inputs": inputs,
            "files": blobs
        }
        response = agente_sap.invoke(input=initial_state)
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

result = ExtractionSap(caso)
# print(result["outputs"])
# with open(file_path_output, "w", encoding="utf-8") as file:
#             json.dump(result, file, ensure_ascii=False, indent=4)