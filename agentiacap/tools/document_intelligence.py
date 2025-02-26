import base64
import logging
import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from openai import AzureOpenAI
from typing import List
from dotenv import load_dotenv
from fastapi import UploadFile
from typing_extensions import TypedDict
#   TODO: EL JSON DEVUELTO POR PROCESS_BASE_64_FILES NO CONTIENE MISSING FIELDS EN SU ESTRUCTURA

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


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
                    - Devuelve las fechas en formato dd-MM-yyyy.
                    - El "PurchaseOrderName" siempre es un número de 10 dígitos referenciado como orden de pago o similares y tiene la caracteristica de que siempre empieza con 2 o con 36. Ejemplos tipicos de este numero pueden ser 2000002154, 2000000831, 2000010953.  No siempre esta presente este dato.
                    -"CustomerName": se refiere a la sociedad por la que se hace la consulta. Solo se pueden incluir las sociedades permitidas en la lista de sociedades.
                    **Lista de sociedades permitidas:
                    -"Nombre Soc SAP": "AESA", "Código SAP": "0478", "Estado": "Activa", "CUIT": "30685211890", "Nombre en AFIP": "ASTRA EVANGELISTA SA"
                    -"Nombre Soc SAP": "YPF GAS", "Código SAP": "0522", "Estado": "Activa", "CUIT": "33555234649", "Nombre en AFIP": "YPF GAS S.A."
                    -"Nombre Soc SAP": "UTE LA VENTANA", "Código SAP": "0571", "Estado": "Activa", "CUIT": "30652671418", "Nombre en AFIP": "YACIMIENTO LA VENTANA YPF SA SINOPEC ARGENTINA EXPLORATION AND PRODUCTION INC UNION TRANSITORIA"
                    -"Nombre Soc SAP": "YPF S.A.", "Código SAP": "0620", "Estado": "Activa", "CUIT": "30546689979", "Nombre en AFIP": "YPF SA",
                    -"Nombre Soc SAP": "Fundación YPF", "Código SAP": "0789", "Estado": "Activa", "CUIT": "30691548054", "Nombre en AFIP": "FUNDACION YPF",
                    -"Nombre Soc SAP": "UTE LLANCANELO", "Código SAP": "0797", "Estado": "Activa", "CUIT": "30707293809", "Nombre en AFIP": "CONTRATO DE UNION TRANSITORIA DE EMPRESAS - AREA LLANCANELO U.T.E.",
                    -"Nombre Soc SAP": "OPESSA", "Código SAP": "0680", "Estado": "Activa", "CUIT": "30678774495", "Nombre en AFIP": "OPERADORAS DE ESTACIONES DE SERVICIO SA",
                    -"Nombre Soc SAP": "UTE CAMPAMENTO CENTRAL CAÑADON PERDIDO", "Código SAP": "0862", "Estado": "Activa", "CUIT": "33707856349", "Nombre en AFIP": "YPF S A - SIPETROL ARGENTINA S A - UTE CAMPAMENTO CENTRAL - CAÑADON PERDIDO",
                    -"Nombre Soc SAP": "UTE BANDURRIA", "Código SAP": "0900", "Estado": "Activa", "CUIT": "30708313587", "Nombre en AFIP": "YPF S.A WINTENSHALL ENERGIA SA - PAN AMERICAN ENERGY LLC AREA BANDURRIA UTE",
                    -"Nombre Soc SAP": "Ute Santo Domingo I y II", "Código SAP": "0901", "Estado": "Activa", "CUIT": "30713651504", "Nombre en AFIP": "GAS Y PETROELO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA - YPF S.A. - AREA SANTO DOMINGO I Y II UTE",
                    -"Nombre Soc SAP": "UTE CERRO LAS MINAS", "Código SAP": "0918", "Estado": "Activa", "CUIT": "30712188061", "Nombre en AFIP": "GAS Y PETROLEO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA-YPF S.A.-TOTAL AUSTRAL SA SUC ARG-ROVELLA ENERGIA SA-AREA CERRO LAS MINAS UTE",
                    -"Nombre Soc SAP": "UTE ZAMPAL OESTE", "Código SAP": "1046", "Estado": "Activa", "CUIT": "30709441945", "Nombre en AFIP": "YPF S.A EQUITABLE RESOURCES ARGENTINA COMPANY S.A - ZAMPAL OESTE UTE",
                    -"Nombre Soc SAP": "UTE ENARSA 1", "Código SAP": "1146", "Estado": "Activa", "CUIT": "30710916833", "Nombre en AFIP": "ENERGIA ARGENTINA S.A.- YPF S.A.- PETROBRAS ENERGIA S.A.- PETROURUGUAY S.A. UNION TRANSITORIAS DE EMPRESAS E1",
                    -"Nombre Soc SAP": "UTE GNL ESCOBAR", "Código SAP": "1153", "Estado": "Activa", "CUIT": "30711435227", "Nombre en AFIP": "ENERGIA ARGENTINA S.A. - YPF S.A. - PROYECTO GNL ESCOBAR - UNION TRANSITORIA DE EMPRESAS",
                    -"Nombre Soc SAP": "UTE RINCON DEL MANGRULLO", "Código SAP": "1160", "Estado": "Activa", "CUIT": "30714428469", "Nombre en AFIP": "YPF S.A - PAMPA ENERGIA S.A.. UNION TRANSITORIA DE EMPRESAS - RINCON DEL MANGRULLO",
                    -"Nombre Soc SAP": "UTE CHACHAHUEN", "Código SAP": "1164", "Estado": "Activa", "CUIT": "30716199025", "Nombre en AFIP": "YPF S.A.-KILWER S.A.-KETSAL S.A.-ENERGIA MENDOCINA S.A. AREA CHACHAHUEN UNION TRANSITORIA DE EMPRESAS",
                    -"Nombre Soc SAP": "UTE La amarga chica", "Código SAP": "1167", "Estado": "Activa", "CUIT": "30714869759", "Nombre en AFIP": "YPF S.A. - PETRONAS E&P ARGENTINA S.A.",
                    -"Nombre Soc SAP": "UTE EL OREJANO", "Código SAP": "1169", "Estado": "Activa", "CUIT": "30715142658", "Nombre en AFIP": "YPF S.A.- PBB POLISUR S.A., AREA EL OREJANO UNION TRANSITORIA",
                    -"Nombre Soc SAP": "CIA HIDROCARBURO NO CONVENCIONAL SRL", "Código SAP": "1171", "Estado": "Activa", "CUIT": "30714124427", "Nombre en AFIP": "COMPAÑIA DE HIDROCARBURO NO CONVENCIONAL S.R.L.",
                    -"Nombre Soc SAP": "UTE PAMPA (YSUR)", "Código SAP": "1632", "Estado": "Activa", "CUIT": "30711689067", "Nombre en AFIP": "APACHE ENERGIA ARGENTINA S.R.L. - PETROLERA PAMPA S.A., UNION TRANSITORIA DE EMPRESAS - ESTACION FERNANDEZ ORO Y ANTICLINAL CAMPAMENTO"
                    **Aclaración sobre lista de sociedades permitidas:**
                    - Cada elemento de la lista hace referencia a una unica sociedad.
                    - Cada apartado de un elemento sirve para identificar a la misma sociedad. Los apartados estan delimitados por ','.
                    - Si detectas un dato de la lista en el documento completa los datos del customer con los datos de la lista para ese customer.
                    - Cualquier nombre de sociedad o CUIT encontrado en el documento que no tenga match con la lista de sociedades deberá interpretarse como dato del Vendor.
                    - El campo "Signed" es un flag (booleano) para indicar si el documento está firmado. En caso de que reconozcas una firma deberás setear este campo como True.
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

    def extract_fields(self, base64_images: list, fields_to_extract: List[str]):
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

                user_content = self.create_user_content(content, fields_to_extract)

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
                        max_tokens=10000,
                        temperature=0.1,
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
                                                    "VendorTaxId": {"type": ["string", "null"]},
                                                    "CustomerAddress": {"type": ["string", "null"]},
                                                    "InvoiceId": {"type": ["string", "null"]},
                                                    "InvoiceDate": {"type": ["string", "null"]},
                                                    "InvoiceTotal": {"type": ["string", "null"]},
                                                    "PurchaseOrderNumber": {"type": ["string", "null"]},
                                                    "Signed": {"type": "boolean"}
                                                },
                                                "required": [
                                                    "VendorName", "CustomerName", "CustomerTaxId", 
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

                    # logging.info(f"Se ha procesado la imagen con el LLM.\nCompletion: \n{completion}")
                    data = self.parse_completion_response(completion)
                    # print(f"Data: \n{data}")
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
