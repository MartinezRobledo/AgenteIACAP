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
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat
from typing import Optional
from pydantic import BaseModel, Field
import pandas as pd
import re

from agentiacap.utils.globals import cods_soc, socs, cuits, lista_sociedades

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

def extract_table_layout(file_bytes: bytes, header_ref: str = None) -> pd.DataFrame:

    def normalizar_header(header: str):
        if header:
            header = header.strip().lower()
            header = re.sub(r"[^\w\s]", "", header)  # elimina signos como º, ., etc.
            header = re.sub(r"\s+", "_", header)     # reemplaza espacios por _
        return header


    client = initialize_client()
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=file_bytes,
        output_content_format=DocumentContentFormat.MARKDOWN,
        content_type="application/pdf"
    )
    
    result: AnalyzeResult = poller.result()
    tablas_validas = []
    ref_error = 0
    ref_column_count = None
    header_detected = False
    header_columns = None

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

        if header_ref:
            header_index = None
            for i, row in df.iterrows():
                if header_ref in row.values:
                    header_index = i
                    break

            if header_index is not None:
                # Se detectó el encabezado
                header_columns = [normalizar_header(col) for col in df.iloc[header_index]]
                ref_column_count = len(header_columns)
                header_detected = True

                df = df[header_index + 1:].reset_index(drop=True)
                df.columns = header_columns
                tablas_validas.insert(0, df)  # encabezado primero
            else:
                if not header_detected:
                    ref_error += 1
                    if ref_error == len(result.tables):
                        raise ValueError(f"D.I. Layout: No se encontró la columna '{header_ref}'.")
                continue
        else:
            if header_detected and df.shape[1] == ref_column_count:
                df.columns = header_columns
                tablas_validas.append(df)

    if not tablas_validas:
        raise ValueError("No se encontraron tablas válidas para concatenar.")

    tabla_final = pd.concat(tablas_validas, ignore_index=True)
    return tabla_final


def extract_table_custom_layout(file_bytes: bytes) -> pd.DataFrame:
    def normalizar_header(header: str):
        if header:
            header = header.strip().lower()
            header = re.sub(r"[^\w\s]", "", header)  # elimina signos como º, ., etc.
            header = re.sub(r"\s+", "_", header)     # reemplaza espacios por _
        return header


    load_dotenv()
    endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_KEY")
    model_id = os.getenv("AZURE_CUSTOM_MODEL_ID")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    poller = client.begin_analyze_document(
        model_id=model_id,
        body=file_bytes,
        content_type="application/pdf"
    )
    result = poller.result()

    # Buscar tabla etiquetada como 'Datos_Sap'
    tabla = result.documents[0].fields.get("Datos_Sap")
    if tabla and tabla.type == "array":
        filas = []
        # Iterar sobre los registros de la tabla
        for fila in tabla.value_array:
            # Extraer cada valor de los campos
            n_doc = fila.value_object.get('N° doc', {}).get('valueString', '')
            clas = fila.value_object.get('Clas', {}).get('valueString', '')
            fecha_doc = fila.value_object.get('Fecha doc', {}).get('valueString', '')
            referencia = fila.value_object.get('Referencia', {}).get('valueString', '')
            fecha_base = fila.value_object.get('Fecha base', {}).get('valueString', '')
            vence_el = fila.value_object.get('Vence el', {}).get('valueString', '')
            impte_mon_extr = fila.value_object.get('Impte.mon.extr', {}).get('valueString', '')
            doc_comp = fila.value_object.get('Doc comp', {}).get('valueString', '')
            compens = fila.value_object.get('Compens', {}).get('valueString', '')
            
            # Agregar la fila extraída al listado de filas
            filas.append({
                'N° doc': n_doc,
                'Clas': clas,
                'Fecha doc': fecha_doc,
                'Referencia': referencia,
                'Fecha base': fecha_base,
                'Vence el': vence_el,
                'Impte.mon.extr': impte_mon_extr,
                'Doc comp': doc_comp,
                'Compens': compens
            })

        # Convertir la lista de filas a un DataFrame
        df = pd.DataFrame(filas)
        df.columns = [normalizar_header(col) for col in df.columns]
    return df
        

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

    def create_user_content(self, base64_data: str, prompt:str):
        """
        Crea el contenido que se enviará al modelo para procesar.
        """
        user_content = [
            {
                "type": "text",
                "text": prompt
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
    
    def parse_completion_response_str(self, completion):
        """
        Procesa la respuesta del modelo para extraer el JSON válido y convertirlo en un diccionario de campos.
        """
        extracted_data = completion.model_dump()
        content = extracted_data["choices"][0]["message"]["content"]
        return content

    def extract_fields(self, base64_images: list, fields_to_extract: list, restrictions: list):
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

                prompt = f"""
                    Extrae los siguientes campos del documento: {', '.join(fields_to_extract)}.
                    - Si un valor no está presente, indica "".
                    - Devuelve las fechas en formato dd-MM-yyyy.
                    - El "PurchaseOrderName" siempre es un número de 10 dígitos referenciado como orden de pago o similares y tiene la caracteristica de que siempre empieza con 2 o con 36. Ejemplos tipicos de este numero pueden ser 2000002154, 2000000831, 2000010953.  No siempre esta presente este dato.
                    -"CustomerName": se refiere a la sociedad por la que se hace la consulta. Solo se pueden incluir las sociedades permitidas en la lista de sociedades.
                    **Lista de sociedades permitidas:
                    {', '.join([str(soc) for soc in restrictions])}
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
                user_content = self.create_user_content(content, prompt)

                messages = [
                    {"role": "system", "content": "Eres un asistente que extrae datos de documentos."},
                    {"role": "user", "content": user_content}
                ]

                total_tokens = 0  # Definir total_tokens antes del try-except

                try:
                    print(f"Se está por procesar la imagen {file_name} con el LLM")
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

                    data = self.parse_completion_response(completion)
                    print(f"Data extraida con VISION: \n{data}")
                    list_data = []
                    for index, element in enumerate(data):

                        list_data.append({
                            "extraction_number": index + 1,
                            "fields": element,
                            "missing_fields": [],
                            "source": "Vision",
                            "tokens": total_tokens
                        })

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

    def es_carta_modelo(self, base64_images):
        """
        Extrae datos específicos de una lista de imágenes en base64 y organiza los resultados en un diccionario.

        :param base64_images: Lista de diccionarios con datos de las imágenes (file_name y content).
        :param fields_to_extract: Lista de campos a extraer.
        :return: Diccionario con los resultados extraídos o información de error.
        """
        try:
            if not base64_images or not isinstance(base64_images, list):
                raise ValueError("La lista de imágenes base64 no es válida.")

            all_results = []

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

                prompt = "Identifica si la siguiente imagen es una carta modelo y si lo es extrae los datos de la carta."
                
                user_content = self.create_user_content(content, prompt)

                messages = [
                    {
                        "role": "system", 
                        "content": f"""
                                Eres un asistente experto en reconocer dos tipos de documentos: "Carta Modelo" y "Certificado de Retenciones".

                                Primero debes analizar el contenido del documento y clasificarlo como uno de los siguientes:
                                - Carta Modelo
                                - Certificado de Retenciones
                                - Documento No Reconocido

                                ### Criterios para reconocer una "Carta Modelo":
                                Este documento tiene formato de carta en la cual se reconocen 4 grupos importantes:

                                1. Se menciona fecha y lugar de la redacción como en toda carta.

                                2. Tiene un texto inicial que debe contener el mensaje: **"dichas retenciones no se computaron ni se computarán"**.  
                                En caso de no mencionar esa expresión textual, **descarta como carta modelo sin importar el resto de los grupos.**

                                3. Luego del texto inicial contiene un listado con datos de facturación, los cuales deben mencionar todos los siguientes campos:
                                - Número completo de la factura a la cual se le aplicó la retención o número de Orden de Pago.
                                - Fecha en que fue realizada la retención.
                                - Impuesto o tasa correspondiente a dicha retención (IVA, Ganancias, Ingresos Brutos, SUSS, etc).
                                - Razón social de la empresa del grupo YPF que aplicó la retención.
                                - Lugar en donde presentó la factura que dio lugar a la retención (seguramente sea una dirección de mail).  
                                Si el listado de facturación menciona otros datos distintos a los mencionados, **descarta el documento como carta modelo.**

                                4. Al pie de página contiene la firma y aclaración del proveedor que redacta la carta.
                                - Se debe reconocer la **firma manuscrita** realizada por una persona.
                                - **Importante:** No debe considerarse como firma cualquier trazo o marca manuscrita aislada.
                                - Para que una firma sea considerada válida, **debe estar asociada directamente con una aclaración** que incluya el **nombre completo y el cargo del firmante.**
                                - Si hay una marca manuscrita pero no tiene aclaración, **no debe tomarse como firma**.
                                - Si hay aclaración sin firma manuscrita, considerar que se trata de una **carta modelo sin firmar**.

                                ---

                                ### Criterios para reconocer un "Certificado de Retenciones":
                                Este documento está dividido claramente en **cuatro secciones horizontales separadas por líneas**. Cada sección cumple una función específica:

                                1. **Primera sección (superior):** Datos de la sociedad o cliente.  
                                - La información está organizada en **dos columnas**.
                                - A la izquierda suele estar el **nombre de la sociedad** y su **dirección**.
                                - A la derecha puede estar el **CUIT**, la **paginación** u otros datos similares.  
                                - El orden puede variar, pero **siempre debe haber dos columnas con datos de la sociedad.**

                                2. **Segunda sección (debajo):** Datos del proveedor.  
                                - También estructurados en **dos columnas**, al igual que los de la sociedad.

                                3. **Tercera sección:** Datos de facturación.  
                                - Se encuentra debajo de los datos del proveedor.
                                - Puede estar en formato de **lista o tabla**, con información como número de factura, fecha, impuesto retenido, etc.

                                4. **Cuarta sección (abajo de todo):** Totales.  
                                - Contiene el **monto total** retenido u otro resumen numérico.

                                ---
                                **Lista de sociedades permitidas:**
                                {lista_sociedades}
                                ---
                                ### Salida esperada:

                                - Si reconoces que el documento es una **Carta Modelo**, devuelve:
                                * `"Es nota modelo": true`
                                * `"Es certificado de retenciones": false`
                                * Razón social y CUIT del proveedor
                                * Fecha en que fue realizada la retención
                                * Razón social (sociedad) de la empresa del grupo YPF:
                                    - Utilizar alguno de los datos encontrados en el documento y autocompletar el resto filtrando con ese dato en la lista de sociedades permitidas.
                                * Lugar donde se presentó la factura
                                * `"Firmada": true/false`
                                * `"Datos completos": true/false`

                                - Si reconoces que es un **Certificado de Retenciones**, devuelve:
                                * `"Es nota modelo": false`
                                * `"Es certificado de retenciones": true`
                                * Datos de la sociedad:
                                    - Utilizar alguno de los datos encontrados en el documento y autocompletar el resto filtrando con ese dato en la lista de sociedades permitidas.
                                * Total retenido (si está presente)
                                * Fecha del encabezado.

                                - Si no es ninguno de los dos documentos:
                                * `"Es nota modelo": false`
                                * `"Es certificado de retenciones": false`
                                * `"Documento no reconocido"` con una explicación de por qué no encaja en ninguno de los formatos.
                        """
                    },
                    {
                        "role": "user", 
                        "content": user_content
                    }
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
                                "name": "nota_modelo_schema",
                                "strict": True,
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "es_nota_modelo": {"type": "boolean"},
                                        "es_certificado_retenciones": {"type": "boolean"},
                                        "datos": {
                                            "type": "object",
                                            "properties": {
                                                "CUIT_proveedor": {"type": "string"},
                                                "CUIT_sociedad": {"type": "string", "enum": cuits},
                                                "nombre_proveedor": {"type": "string"},
                                                "nombre_sociedad": {"type": "string", "enum": socs},
                                                "codigo_sociedad": {"type": "string", "enum": cods_soc},
                                                "total": {"type": "string"},
                                                "fecha": {"type": "string"}
                                            },
                                            "required": ["CUIT_proveedor", "CUIT_sociedad", "nombre_proveedor", "nombre_sociedad", "codigo_sociedad", "total", "fecha"],
                                            "additionalProperties": False
                                        },
                                        "datos_completos": {"type": "boolean"},
                                        "firmada": {"type": "boolean"}
                                    },
                                    "required": ["es_nota_modelo", "es_certificado_retenciones", "datos", "datos_completos", "firmada"],
                                    "additionalProperties": False
                                }
                            }
                        }
                    )

                    data = self.parse_completion_response_str(completion)
                    print(f"Data extraida con VISION: \n{data}")
                    all_results.append(
                        {
                            "file_name": file_name, 
                            "source":"Vision",
                            "extractions": {
                                **json.loads(data)
                            } 
                        }
                    )

                    logging.info(f"Resultados de la imagen {file_name} guardados")
                except Exception as model_error:
                    all_results[file_name] = {"error": str(model_error)}

            return all_results
        except Exception as e:
            return {"error": str(e)}
