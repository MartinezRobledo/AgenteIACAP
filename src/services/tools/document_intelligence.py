import base64
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

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
        "results": [],
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

def analyze_image(client, file_bytes: bytes, fields_to_extract: list) -> dict:
    """
    Analiza una imagen y extrae datos definidos en fields_to_extract.
    :param client: Cliente de Azure Document Intelligence.
    :param file_bytes: Contenido de la imagen en bytes.
    :param fields_to_extract: Campos que se desean extraer de la imagen.
    :return: Diccionario con los resultados de la extracción.
    """
    print("Analizando imagen...")
    data = {
        "results": [],
        "missing_fields": [],
        "error": ""
    }
    try:
        # Iniciar el análisis con el modelo prebuilt-document
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
            data["error"] = "No se encontraron documentos en la imagen."

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
                print("No se encontraron los campos: ", text_result["missing_fields"])
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
                "results": text_result["results"],
                "error": text_result["error"]
            })

        except Exception as e:
            final_results.append({
                "file_name": file_name,
                "results": [],
                "error": str(e)
            })

    return final_results

def process_base64_images(base64_images: list, fields_to_extract: list) -> list:
    """
    Procesa una lista de imágenes en formato base64 y extrae los campos indicados.
    :param base64_images: Lista de diccionarios con nombre y contenido base64 de las imágenes.
    :param fields_to_extract: Campos que se desean extraer de las imágenes.
    :return: Lista con los resultados de extracción por imagen.
    """
    client = initialize_client()
    final_results = []

    for image_data in base64_images:
        file_name = image_data.get("file_name", "unknown")
        base64_content = image_data.get("base64_content", "")

        try:
            file_bytes = base64.b64decode(base64_content)

            # Llamar a la función analyze_image para extraer datos
            image_result = analyze_image(client, file_bytes, fields_to_extract)

            final_results.append({
                "file_name": file_name,
                "results": image_result["results"],
                "error": image_result["error"]
            })

        except Exception as e:
            final_results.append({
                "file_name": file_name,
                "results": [],
                "error": str(e)
            })

    return final_results

# Ejemplo de uso
# if __name__ == "__main__":
#     base64_images = [
#         {"file_name": "image1.png", "base64_content": "<base64_string1>"},
#         {"file_name": "image2.jpg", "base64_content": "<base64_string2>"}
#     ]  # Reemplaza <base64_string1> y <base64_string2> con los datos base64 reales
#     fields_to_extract = ["InvoiceId", "CustomerName", "TotalAmount"]

#     results = process_base64_images(base64_images, fields_to_extract)
#     print(results)

# Ejemplo de uso
# if __name__ == "__main__":
#     base64_files = [
#         {"file_name": "invoice1.pdf", "base64_content": "<base64_string1>"},
#         {"file_name": "invoice2.pdf", "base64_content": "<base64_string2>"}
#     ]  # Reemplaza <base64_string1> y <base64_string2> con los datos base64 reales
#     fields_to_extract = ["InvoiceId", "CustomerName", "TotalAmount"]

#     results = process_base64_files(base64_files, fields_to_extract)
#     print(results)
