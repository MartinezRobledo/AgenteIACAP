import base64
import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from openai import AzureOpenAI
from typing import List
from dotenv import load_dotenv

#   TODO: EL JSON DEVUELTO POR PROCESS_BASE_64_FILES NO CONTIENE MISSING FIELDS EN SU ESTRUCTURA

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


def initialize_client():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    return DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

def analyze_document_text_based(client, file_bytes: bytes, fields_to_extract: list) -> dict:
    print("Analizando documento basado en texto...")
    data = {
        "results": [],
        "missing_fields": [],
        "error": ""
    }
    try:
        poller = client.begin_analyze_document(
            "prebuilt-invoice", AnalyzeDocumentRequest(bytes_source=file_bytes)
        )
        invoices = poller.result()

        if invoices.documents:
            for idx, invoice in enumerate(invoices.documents):
                invoice_data = []

                for field in fields_to_extract:
                    field_data = invoice.fields.get(field)
                    if field_data:
                        invoice_data.append({
                            "field": field,
                            "value": field_data.content,
                            "confidence": field_data.confidence,
                        })
                    else:
                        data["missing_fields"].append(field)
                        invoice_data.append({
                            "field": field,
                            "value": "No encontrado",
                            "confidence": 0
                        })

                data["results"].append({
                    "invoice_number": idx + 1,
                    "fields": invoice_data
                })
        else:
            data["error"] = "No se encontraron documentos en el archivo."

    except Exception as e:
        data["error"] = str(e)

    return data

def analyze_document_vision_based(client, file_bytes: bytes, fields_to_extract: list) -> dict:
    print("Analizando documento basado en vision...")
    data = {
        "fields": [],
        "missing_fields": [],
        "error": ""
    }
    try:
        poller = client.begin_analyze_document(
            "prebuilt-document", AnalyzeDocumentRequest(bytes_source=file_bytes)
        )
        documents = poller.result()

        if documents.documents:
            for idx, document in enumerate(documents.documents):
                document_data = []

                for field in fields_to_extract:
                    field_data = document.fields.get(field)
                    if field_data:
                        document_data.append({
                            "field": field,
                            "value": field_data.content,
                            "confidence": field_data.confidence,
                        })
                    else:
                        data["missing_fields"].append(field)
                        document_data.append({
                            "field": field,
                            "value": "No encontrado",
                            "confidence": 0
                        })

                data["results"].append({
                    "document_number": idx + 1,
                    "fields": document_data
                })
        else:
            data["error"] = "No se encontraron documentos en el archivo."

    except Exception as e:
        data["error"] = str(e)

    return data

def process_base64_files(base64_files: list, fields_to_extract: list) -> list:
    client = initialize_client()
    final_results = []

    for file_data in base64_files:
        file_name = file_data.get("file_name", "unknown")
        base64_content = file_data.get("base64_content", "")

        try:
            file_bytes = base64.b64decode(base64_content)

            # Intentar con text-based primero
            text_result = analyze_document_text_based(client, file_bytes, fields_to_extract)

            if text_result["missing_fields"]:
                # Si faltan campos, intentar con vision-based
                vision_result = analyze_document_vision_based(client, file_bytes, text_result["missing_fields"])
                
                # Fusionar resultados
                for text, vision in zip(text_result["results"], vision_result["results"]):
                    for field in vision["fields"]:
                        if field["value"] != "No encontrado":
                            # Actualizar el valor y confianza si fue encontrado en vision
                            for text_field in text["fields"]:
                                if text_field["field"] == field["field"]:
                                    text_field["value"] = field["value"]
                                    text_field["confidence"] = field["confidence"]

            final_results.append({
                "file_name": file_name,
                "fields": text_result["results"],
                "missing_fields": text_result["missing_fields"],
                "error": text_result["error"]
            })

        except Exception as e:
            final_results.append({
                "file_name": file_name,
                "fields": [],
                "missing_fields": [],
                "error": str(e)
            })

    return final_results


class ImageFieldExtractor:
    def __init__(self):
        """
        Inicializa el cliente de OpenAI en Azure.
        :param openai_endpoint: Endpoint de Azure OpenAI.
        :param gpt_model_name: Nombre del modelo GPT configurado en Azure.
        :param api_key: Clave de la API para autenticación.
        :param api_version: Versión de la API de Azure OpenAI.
        """
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
            api_key=os.getenv("OPENAI_API_KEY"),  # Usamos la API key para autenticación
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
        self.gpt_model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

    def create_user_content(self, base64_data: str, fields_to_extract: List[str]):
        """
        Crea el contenido que se enviará al modelo para procesar.
        """
        user_content = [
            {
                "type": "text",
                "text": f"""
                    Extrae los siguientes campos del documento: {', '.join(fields_to_extract)}.
                    - Si un valor no está presente, indica null.
                    - Devuelve las fechas en formato YYYY-MM-DD.
                """
            }
        ]
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64_data}"}
        })
        return user_content

    def parse_completion_response(self, completion):
        """
        Procesa la respuesta del modelo para extraer el JSON válido y convertirlo en un diccionario de campos.
        """
        extracted_data = completion.model_dump()
        content = extracted_data['choices'][0]['message']['content']
        json_content = content.strip('```json\n').strip('```')
        data = json.loads(json_content)

        return data

    def extract_fields(self, base64_images: list, fields_to_extract: List[str]):
        """
        Extrae datos específicos de una lista de imágenes en base64 y organiza los resultados.

        :param base64_images: Lista de diccionarios con datos de las imágenes (file_name y base64_content).
        :param fields_to_extract: Lista de campos a extraer.
        :return: Diccionario con los resultados extraídos o información de error.
        """
        try:
            # Validar entradas
            if not base64_images or not isinstance(base64_images, list):
                raise ValueError("La lista de imágenes base64 no es válida.")
            if not fields_to_extract or not isinstance(fields_to_extract, list):
                raise ValueError("La lista de campos a extraer no es válida.")

            # Lista para acumular resultados
            all_results = []

            for index, image_data in enumerate(base64_images):
                file_name = image_data.get("file_name", f"unknown_{index + 1}")
                base64_content = image_data.get("base64_content", "")

                # Validar contenido base64 de la imagen
                if not base64_content:
                    print(f"El archivo {file_name} no contiene datos base64.")
                    all_results.append({
                        "file_name": file_name,
                        "fields": [],
                        "missing_fields": [],  # Si no hay datos, no hay campos que analizar
                        "error": "El contenido base64 está vacío."
                    })
                    continue

                # Crear contenido del usuario para enviar al modelo
                user_content = self.create_user_content(base64_content, fields_to_extract)

                # Configurar mensajes para el modelo
                messages = [
                    {"role": "system", "content": "Eres un asistente que extrae datos de documentos."},
                    {"role": "user", "content": user_content}
                ]

                try:
                    # Llamar al modelo OpenAI en Azure
                    completion = self.openai_client.beta.chat.completions.parse(
                        model=self.gpt_model_name,
                        messages=messages,
                        max_tokens=3000,
                        temperature=0.1,
                        top_p=0.1,
                        logprobs=True,
                    )

                    # Extraer tokens usados
                    prompt_tokens = completion.usage.prompt_tokens
                    completion_tokens = completion.usage.completion_tokens
                    total_tokens = prompt_tokens + completion_tokens
                    print(f"Tokens usados para {file_name}: {total_tokens} (Prompt: {prompt_tokens}, Completion: {completion_tokens})")

                    # Procesar respuesta del modelo
                    data = self.parse_completion_response(completion)

                    # Crear los campos en el formato esperado
                    fields = [
                        {
                            "field": field_name,
                            "value": data.get(field_name, None),
                            "confidence": None  # Ajustar si se incluye la confianza en el futuro
                        }
                        for field_name in fields_to_extract
                    ]

                    # Identificar campos faltantes
                    missing_fields = [field for field in fields_to_extract if data.get(field) is None]

                    # Agregar resultados de esta imagen
                    all_results.append({
                        "file_name": file_name,
                        "fields": [
                            {
                                "invoice_number": index + 1,
                                "fields": fields
                            }
                        ],
                        "missing_fields": missing_fields,  # Ahora cada archivo tiene su propia lista de faltantes
                        "error": ""
                    })

                except Exception as model_error:
                    # Manejo de errores al llamar al modelo o procesar su respuesta
                    print(f"Error procesando la imagen {file_name}: {model_error}")
                    all_results.append({
                        "file_name": file_name,
                        "fields": [],
                        "missing_fields": [],  # Si hay error, no hay campos analizados
                        "error": str(model_error)
                    })

            return all_results
        except Exception as e:
            # Manejo de errores general
            print(f"Error general al extraer campos: {e}")
            return {
                "fields": [],
                "missing_fields": [],
                "error": str(e)
            }




# Ejemplo de uso
# if __name__ == "__main__":
#     base64_files = [
#         {"file_name": "invoice1.pdf", "base64_content": "<base64_string1>"},
#         {"file_name": "invoice2.pdf", "base64_content": "<base64_string2>"}
#     ]  # Reemplaza <base64_string1> y <base64_string2> con los datos base64 reales
#     fields_to_extract = ["InvoiceId", "CustomerName", "TotalAmount"]

#     results = process_base64_files(base64_files, fields_to_extract)
#     print(results)
