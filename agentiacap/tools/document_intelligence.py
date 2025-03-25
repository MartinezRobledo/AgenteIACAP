import base64
import io
import logging
import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
import fitz
from openai import AzureOpenAI
from typing import List
from dotenv import load_dotenv
from fastapi import UploadFile
from typing_extensions import TypedDict
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat
from agentiacap.tools.convert_pdf import pdf_binary_to_images_base64
from typing import Optional
from pydantic import BaseModel, Field
import pandas as pd
#   TODO: EL JSON DEVUELTO POR PROCESS_BASE_64_FILES NO CONTIENE MISSING FIELDS EN SU ESTRUCTURA

class SapReg(BaseModel):

    invoice: Optional[str] = Field(
        description='Dato ubicado en la columna "Referencia" y cumple con ser un numero con el formato ddddAdddddddd'
    )
    date: Optional[str] = Field(
        description='Dato ubicado en la columna "FechaDoc" y cumple con ser una fecha formato dd.MM.yyyy'
    )
    due_date: Optional[str] = Field(
        description='Dato ubicado en la columna "Vence El" y cumple con ser una fecha formato dd.MM.yyyy'
    )
    purchase_number: Optional[str] = Field(
        description='Dato ubicado en la columna "Nº doc." y cumple con ser un numero de 10 digitos'
    )
    op_date: Optional[str] = Field(
        description='Dato ubicado en la columna "Fecha doc." y representa la fecha de purchase_number'
    )
    comp_doc: Optional[str] = Field(
        description='Dato ubicado en la columna "Doc. comp." y representa la fecha de purchase_number'
    )
    comp_date: Optional[str] = Field(
        description='Dato ubicado en la columna "Compens." y representa la fecha de purchase_number'
    )
    found: Optional[bool] = Field(
        description='Indica si se encontró el purchase_number. Por defecto es False'
    )
    overdue: Optional[bool] = Field(
        description='Indica si True si la fecha actual es mayor a la fecha de due_date. Por defecto es False'
    )

class SapTable(BaseModel):
    """
    A class representing a table of invoices with multiple rows.
    
    Attributes:
        invoices: A list of Invoice objects.
    """
    invoices: List[SapReg]

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceTable object.

        Returns:
            InvoiceTable: An empty InvoiceTable object with no invoices.
        """
        return SapTable(invoices=[])

# Cargar las variables de entorno desde el archivo .env
load_dotenv(override=True)


def initialize_client():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    return DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

def analyze_document_prebuilt_invoice(client, file_bytes: bytes, fields_to_extract: list) -> list:
    data = []
    try:
        poller = client.begin_analyze_document(
            "prebuilt-invoice", AnalyzeDocumentRequest(bytes_source=file_bytes)
        )
        invoices = poller.result()

        if invoices.documents:
            for idx, invoice in enumerate(invoices.documents):
                fields_data = {}
                missing_fields = []
                
                for field in fields_to_extract:
                    field_data = invoice.fields.get(field)
                    if field_data:
                        fields_data[field] = field_data.content
                    else:
                        fields_data[field] = "none"
                        missing_fields.append(field)
                
                data.append({
                    "extraction_number": idx + 1,
                    "fields": fields_data,
                    "missing_fields": missing_fields,
                    "error": "",
                    "source": "Document Intelligence"
                })
        else:
            data = [{
                    "extraction_number": 0,
                    "fields": {},
                    "missing_fields": [],
                    "error": "No se encontraron documentos en el archivo.",
                    "source": "Document Intelligence"
                }]
    
    except Exception as e:
        data = [{
                    "extraction_number": 0,
                    "fields": {},
                    "missing_fields": [],
                    "error": str(e),
                    "source": "Document Intelligence"
                }]
    
    return data


def extract_table_layout(file_bytes: bytes, header_ref: str = None) -> list:
    client = initialize_client()
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout", 
        body=file_bytes,
        output_content_format=DocumentContentFormat.MARKDOWN,
        content_type="application/pdf"
    )

    result: AnalyzeResult = poller.result()
    tables = []

    for table_idx, table in enumerate(result.tables):
        print(f"Table # {table_idx} has {table.row_count} rows and {table.column_count} columns")

        table_data = []

        for row_idx in range(table.row_count):
            row_data = []
            for col_idx in range(table.column_count):
                cell = next((cell for cell in table.cells if cell.row_index == row_idx and cell.column_index == col_idx), None)
                row_data.append(cell.content if cell else None)
            table_data.append(row_data)

        df = pd.DataFrame(table_data)

        # Si se proporciona header_ref, buscar la fila con el encabezado
        if header_ref:
            header_index = None
            for i, row in df.iterrows():
                if header_ref in row.values:
                    header_index = i
                    break

            if header_index is None:
                raise ValueError(f"D.I. Layout: No se encontró la referencia '{header_ref}' en la tabla {table_idx}.")

            df.columns = df.iloc[header_index]  # Usar esa fila como encabezado
            df = df[header_index + 1:].reset_index(drop=True)  # Tomar solo las filas siguientes

        tables.append(df)

    return tables
        

def process_base64_files(base64_files: list, fields_to_extract: list) -> list:
    client = initialize_client()
    final_results = {}

    for file_data in base64_files:
        file_name = file_data.get("file_name", "unknown")
        content = file_data.get("content", "")

        try:
            file_bytes = base64.b64decode(content)
            text_result = analyze_document_prebuilt_invoice(client, file_bytes, fields_to_extract)
            
            final_results[file_name] = {
                "invoice_number": text_result["invoice_number"],
                "fields": text_result["fields"],
                "missing_fields": text_result["missing_fields"],
                "error": text_result["error"],
                "source": "Document Intelligence"
            }

        except Exception as e:
            final_results[file_name] = {
                "invoice_number": 0,
                "fields": {},
                "missing_fields": [],
                "error": str(e),
                "source": "Document Intelligence"
            }
    
    return [final_results]

def process_uploaded_files(uploaded_files: List[UploadFile], fields_to_extract: List[str]) -> list:
    client = initialize_client()
    final_results = {}

    for file in uploaded_files:
        file_name = file.filename
        try:
            file_bytes = file.file.read()
            text_result = analyze_document_prebuilt_invoice(client, file_bytes, fields_to_extract)
            
            final_results[file_name] = {
                "invoice_number": text_result["invoice_number"],
                "fields": text_result["fields"],
                "missing_fields": text_result["missing_fields"],
                "error": text_result["error"],
                "source": "Document Intelligence"
            }
        except Exception as e:
            final_results[file_name] = {
                "invoice_number": 0,
                "fields": {},
                "missing_fields": [],
                "error": str(e),
                "source": "Document Intelligence"
            }
    
    return [final_results]

def process_binary_files(binary_files: list, fields_to_extract: list) -> list:
    client = initialize_client()
    final_results = {}

    for file_data in binary_files:
        file_name = file_data.get("file_name", "unknown")
        content = file_data.get("content", b"")

        try:
            text_result = analyze_document_prebuilt_invoice(client, content, fields_to_extract)
            
            final_results[file_name] = text_result

        except Exception as e:
            final_results[file_name] = [{
                "invoice_number": 0,
                "fields": {},
                "missing_fields": [],
                "error": str(e),
                "source": "Document Intelligence"
            }]
    
    return [final_results]

def split_pdf_in_pages(pdf_bytes):
    """
    Desglosa un PDF en memoria en páginas y devuelve una lista con cada página en formato binario.

    :param pdf_bytes: Bytes del archivo PDF (por ejemplo, desde BytesIO).
    :return: Lista de bytes, donde cada elemento representa una página en formato PDF.
    """
    doc = fitz.open("pdf", pdf_bytes)  # Abrir desde bytes
    paginas = []

    for pagina in doc:
        pdf_nuevo = fitz.open()  # Crear un nuevo PDF en memoria
        pdf_nuevo.insert_pdf(doc, from_page=pagina.number, to_page=pagina.number)
        
        buffer = io.BytesIO()
        pdf_nuevo.save(buffer)  # Guardar en memoria
        pdf_nuevo.close()
        
        paginas.append(buffer.getvalue())  # Obtener los bytes de la página
    
    doc.close()
    return paginas  # Lista de binarios

# def find_in_binary_files_layout(file_name:str, binary_file, mothod_prompt:str) -> list:
#     client = initialize_client()
#     final_results = {}
#     try:
#         # Se usa el modelo Layout en lugar del modelo Invoice
#         text_result = analyze_document_layout(client, binary_file, mothod_prompt)
        
#         final_results[file_name] = text_result

#     except Exception as e:
#         final_results[file_name] = {
#             "document_id": 0,
#             "fields": {},
#             "missing_fields": [],
#             "error": str(e),
#             "source": "Document Intelligence - Layout"
#         }
    
#     return [final_results]

class ImageFieldExtractor:
    def __init__(self):
        """
        Inicializa el cliente de OpenAI en Azure.
        :param openai_endpoint: Endpoint de Azure OpenAI.
        :param gpt_model_name: Nombre del modelo GPT configurado en Azure.
        :param api_key: Clave de la API para autenticación.
        :param api_version: Versión de la API de Azure OpenAI.
        """
        print("API VERSION: ",os.getenv("AZURE_OPENAI_API_VERSION"))
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  # Usamos la API key para autenticación
            api_version="2024-08-01-preview"#os.getenv("AZURE_OPENAI_API_VERSION"),
        )
        self.gpt_model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

    def create_user_content(self, base64_data: str, fields_to_extract: List[str], restrictions: list):
        """
        Crea el contenido que se enviará al modelo para procesar.
        """
        user_content = [
            {
                "type": "text",
                "text": f"""
                    Extrae los siguientes campos del documento: {', '.join(fields_to_extract)}.
                    - Si un valor no está presente, indica "".
                    - Devuelve las fechas en formato dd-MM-yyyy.
                    - El "PurchaseOrderName" siempre es un número de 10 dígitos referenciado como orden de pago o similares y tiene la caracteristica de que siempre empieza con 2 o con 36. Ejemplos tipicos de este numero pueden ser 2000002154, 2000000831, 2000010953.  No siempre esta presente este dato.
                    -"CustomerName": se refiere a la sociedad por la que se hace la consulta. Solo se pueden incluir las sociedades permitidas en la lista de sociedades.
                    **Lista de sociedades permitidas:
                    {restrictions}
                    **Aclaración sobre lista de sociedades permitidas:**
                    - Cada elemento de la lista hace referencia a una unica sociedad.
                    - Cada apartado de un elemento sirve para identificar a la misma sociedad. Los apartados estan delimitados por ','.
                    - Si detectas un dato de la lista en el documento completa los datos del customer con los datos de la lista para ese customer.
                    - Cualquier nombre de sociedad o CUIT encontrado en el documento que no tenga match con la lista de sociedades deberá interpretarse como dato del Vendor.
                    - El campo "Signed" es un flag (booleano) para indicar si el documento está firmado. En caso de que reconozcas una firma deberás setear este campo como True.

                    **Aclaraciones generales:**
                    - Un documento puede tener mas de un InvoiceId.
                    - El InvoiceId es un número de de 8 digitos que suele tener delante un número de 4 digitos separado por un "-" o una letra mayúscula.
                    - CustomerCodSap no se va a encontrar sobre el documento, se debe completar con 'Código SAP' de la lista de sociedades que le corresponda al Customer encontrado. Si no se encuentra ningun customer completar con "".

                    - NO INVENTES NINGUN DATO. SI EXSISTE ALGUN DATO QUE NO ENCUENTRES EN LA IMAGEN BRINDADA, NO LO OTORGUES EN LA RESPUESTA SI TE VES FORZADO A COMPLETAR CON UN VALOR USA UN STRING VACIO POR DEFECTO.
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
        content = extracted_data["choices"][0]["message"]["content"]
        data = json.loads(content)
        invoices = data.get("invoices",[])

        return invoices

    def extract_fields(self, base64_images: list, fields_to_extract: List[str], restrictions: list):
        """
        Extrae datos específicos de una lista de imágenes en base64 y organiza los resultados en un diccionario.

        :param base64_images: Lista de diccionarios con datos de las imágenes (file_name y content).
        :param fields_to_extract: Lista de campos a extraer.
        :return: Diccionario con los resultados extraídos o información de error.
        """
        try:
            if not base64_images or not isinstance(base64_images, list):
                raise ValueError("La lista de imágenes base64 no es válida.")
            if not fields_to_extract or not isinstance(fields_to_extract, list):
                raise ValueError("La lista de campos a extraer no es válida.")

            all_results = {}

            for index, image_data in enumerate(base64_images):
                file_name = image_data.get("file_name", f"unknown_{index + 1}")
                content = image_data.get("content", "")

                if not content:
                    all_results[file_name] = [{
                        "fields": {},
                        "missing_fields": [],
                        "error": "El contenido base64 está vacío.",
                        "source": "Vision"
                    }]
                    continue
                # Intentar decodificar para validar contenido base64
                try:
                    base64.b64decode(content, validate=True)
                except Exception as error:
                    error_message = f"El contenido del archivo en base64 no es válido. Error: {error}"
                    all_results[file_name] = [{
                        "fields": {},
                        "missing_fields": [],
                        "error": error_message,
                        "source": "Vision"
                    }]
                    continue

                user_content = self.create_user_content(content, fields_to_extract, restrictions)

                messages = [
                    {"role": "system", "content": "Eres un asistente que extrae datos de documentos."},
                    {"role": "user", "content": user_content}
                ]

                total_tokens = 0  # Definir total_tokens antes del try-except

                try:
                    logging.info(f"Se está por procesar la imagen {file_name} con el LLM")
                    completion = self.openai_client.chat.completions.create(
                        model=self.gpt_model_name,
                        messages=messages,
                        max_tokens=16384,
                        temperature=0,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "invoice_extraction",
                                "strict": True,
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "invoices": {  # Ahora el array está dentro de un objeto
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "VendorName": {"type": ["string", "null"]},
                                                    "CustomerName": {"type": ["string", "null"]},
                                                    "CustomerTaxId": {"type": ["string", "null"]},
                                                    "CustomerCodSap": {"type": ["string", "null"]},
                                                    "VendorTaxId": {"type": ["string", "null"]},
                                                    "CustomerAddress": {"type": ["string", "null"]},
                                                    "InvoiceId": {"type": ["string", "null"]},
                                                    "InvoiceDate": {"type": ["string", "null"]},
                                                    "InvoiceTotal": {"type": ["string", "null"]},
                                                    "PurchaseOrderNumber": {"type": ["string", "null"]},
                                                    "Signed": {"type": "boolean"}
                                                },
                                                "required": [
                                                    "VendorName", "CustomerName", "CustomerTaxId", "CustomerCodSap",
                                                    "VendorTaxId", "CustomerAddress", "InvoiceId", 
                                                    "InvoiceDate", "InvoiceTotal", "PurchaseOrderNumber", "Signed"
                                                ],
                                                "additionalProperties": False
                                            }
                                        }
                                    },
                                    "required": ["invoices"],
                                    "additionalProperties": False
                                }
                            }
                        }
                    )

                    # print(f"Se ha procesado la imagen con el LLM.\nCompletion: \n{completion}")
                    data = self.parse_completion_response(completion)
                    print(f"Data extraida con VISION: \n{data}")
                    list_data = []
                    for index, element in enumerate(data):
                        # print("Index: ",index)
                        # print("Value: ",element)
                        list_data.append({
                            "extraction_number": index + 1,
                            "fields": element,
                            "missing_fields": [],
                            "source": "Vision",
                            "tokens": total_tokens
                        })
                    # prompt_tokens = getattr(completion.usage, "prompt_tokens", 0)
                    # completion_tokens = getattr(completion.usage, "completion_tokens", 0)
                    # total_tokens = prompt_tokens + completion_tokens
                    all_results[file_name] = list_data
                    logging.info(f"Resultados de la imagen {file_name} guardados")
                except Exception as model_error:
                    all_results[file_name] = [{
                        "fields": {},
                        "missing_fields": [],
                        "error": str(model_error),
                        "source": "Vision",
                        "tokens": total_tokens
                    }]

            return [all_results]
        except Exception as e:
            return {"error": str(e)}

    def extract_fields_binary(self, binary_images: list, fields_to_extract: List[str]):
        """
        Extrae datos específicos de una lista de imágenes en binario y organiza los resultados en un diccionario.

        :param binary_images: Lista de diccionarios con datos de las imágenes (file_name y content en binario).
        :param fields_to_extract: Lista de campos a extraer.
        :return: Diccionario con los resultados extraídos o información de error.
        """
        try:
            if not binary_images or not isinstance(binary_images, list):
                raise ValueError("La lista de imágenes en binario no es válida.")
            if not fields_to_extract or not isinstance(fields_to_extract, list):
                raise ValueError("La lista de campos a extraer no es válida.")

            all_results = {}

            for index, image_data in enumerate(binary_images):
                file_name = image_data.get("file_name", f"unknown_{index + 1}")
                content = image_data.get("content", b"")  # Ahora es binario

                if not content:
                    all_results[file_name] = {
                        "fields": {},
                        "missing_fields": [],
                        "error": "El contenido de la imagen está vacío.",
                        "source": "Vision"
                    }
                    continue

                # Crear input con el contenido binario
                user_content = self.create_user_content(content, fields_to_extract)

                messages = [
                    {"role": "system", "content": "Eres un asistente que extrae datos de documentos."},
                    {"role": "user", "content": user_content}
                ]

                total_tokens = 0  # Definir total_tokens antes del try-except

                try:
                    completion = self.openai_client.chat.completions.create(
                        model=self.gpt_model_name,
                        messages=messages,
                        max_tokens=10000,
                        temperature=0.1,
                        top_p=0.1
                    )


                    # Asegurar que total_tokens siempre esté definido
                    prompt_tokens = getattr(completion.usage, "prompt_tokens", 0)
                    completion_tokens = getattr(completion.usage, "completion_tokens", 0)
                    total_tokens = prompt_tokens + completion_tokens

                    data = self.parse_completion_response(completion)

                    # Crear el diccionario de campos extraídos
                    extracted_fields = {field_name: data.get(field_name, None) for field_name in fields_to_extract}

                    # Identificar campos faltantes
                    missing_fields = [field for field, value in extracted_fields.items() if value is None]

                    # Guardar resultados en un diccionario
                    all_results[file_name] = {
                        "invoice_number": index + 1,
                        "fields": extracted_fields,
                        "missing_fields": missing_fields,
                        "error": "",
                        "source": "Vision",
                        "tokens": total_tokens
                    }

                except Exception as model_error:
                    all_results[file_name] = {
                        "fields": {},
                        "missing_fields": [],
                        "error": str(model_error),
                        "source": "Vision",
                        "tokens": total_tokens
                    }

            return all_results
        except Exception as e:
            return {"error": str(e)}

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     file_path = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Ejemplos SAP y Esker\\CAP123Doc.pdf"
#     with open(file_path, "rb") as f:
#         file_bytes = f.read()
#     fields_to_extract = ["purchase_number", "due_date"]
#     user_text_prompt = f"""Extrae los datos de la tabla siguiendo estos pasos:
#     **Aclaración: Solo se debe ejecutar el flujo alternativo si el flujo principal lo solicita explícitamente.
#     **Flujo principal (obligatorio):
#         - Busca en la columna "Referencia" el numero de factura: {''}. Si no encontras la factura intenta el flujo alternativo.
#         - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp." y obtene 'due_date' de la columna "Vence El". Si no encontras el numero retorna en este punto.
#         - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
#         - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'purchase_number' y el la fecha 'op_date' de la columna "Fecha doc.".
#     **Flujo alternativo (Opcional):
#         - Busca en la columna "Fecha doc." la fecha: {'02.01.2025'}. Si no encontras la fecha retorna.
#         - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp." y obtene 'due_date' de la columna "Vence El". Si no encontras el numero retorna en este punto.
#         - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
#         - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'op' y el la fecha 'op_date' de la columna "Fecha doc.".
#     **Retorno:
#         - Se debe devolver unicamente los datos que se conocen.
#         - Los datos que no se encontraron se deben indicar como un string vacío.
#         - El campo found es un bool que indica si se encontró o no el numero de 10 digitos correspondiente a purchase_number.
#         - El campo overdue es un bool que indica si la fecha actual es mayor a la fecha de vencimeinto que corresponde al campo due_date."""
#     client = initialize_client()
#     result = analyze_document_layout(client, file_bytes, fields_to_extract, user_text_prompt)

#     print("Resultado de la extracción:", result)