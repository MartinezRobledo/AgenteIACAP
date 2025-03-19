import base64
import operator
import json
import logging
from collections import defaultdict
from pydantic import BaseModel
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated, List, Literal, Optional, Sequence
from langgraph.graph import StateGraph, START, END
from agentiacap.tools.document_intelligence import ImageFieldExtractor, process_binary_files, find_in_binary_files_layout
from agentiacap.utils.globals import InputSchema
from agentiacap.llms.llms import llm4o
from agentiacap.llms.Prompts import TextExtractorPrompt, fields_to_extract, merger_definition 
from agentiacap.tools.convert_pdf import pdf_binary_to_images_base64
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from agentiacap.utils.globals import lista_sociedades

# Configuración del logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

socs = [soc["Nombre Soc SAP"] for soc in lista_sociedades] + [soc["Nombre en AFIP"] for soc in lista_sociedades]
cods_soc = [soc["Código SAP"] for soc in lista_sociedades]
cuits = [soc["CUIT"] for soc in lista_sociedades]

json_schema_names = {
    "name": "fixer_schema",
    "schema": {
        "type": "object",
        "properties": {
            "final_answer": {
                "type": "object",
                "properties": {
                    "VendorName": {"type": ["string", "null"]},
                    "CustomerName": {"type": ["string", "null"],
                                    "enum": socs},
                    "CustomerTaxId": {"type": ["string", "null"],
                                    "enum": cuits},
                    "CustomerCodSap": {"type": ["string", "null"],
                                    "enum": cods_soc},
                    "VendorTaxId": {"type": ["string", "null"]}
                },
                "required": [
                    "VendorName", "CustomerName", "CustomerTaxId", "CustomerCodSap", 
                    "VendorTaxId"
                ],
                "additionalProperties": False
            }
        },
        "required": ["final_answer"],
        "additionalProperties": False
    },
    "strict": True
}
json_schema_invoices = {
    "name": "fixer_schema",
    "schema": {
        "type": "object",
        "properties": {
            "final_answer": {
                "type": "object",
                "properties": {
                    "InvoiceId": {
                        "type": ["array", "null"],
                        "items": {"type": "string"}
                    },
                    "InvoiceDate": {
                        "type": ["array", "null"],
                        "items": {"type": "string"}
                    },
                    "InvoiceTotal": {"type": ["string", "null"]},
                    "PurchaseOrderNumber": {"type": ["string", "null"]}
                },
                "required": [
                    "InvoiceId", "InvoiceDate", 
                    "InvoiceTotal", "PurchaseOrderNumber"
                ],
                "additionalProperties": False
            }
        },
        "required": ["final_answer"],
        "additionalProperties": False
    },
    "strict": True
}
json_schema = {
    "name": "fixer_schema",
    "schema": {
        "type": "object",
        "properties": {
            "final_answer": {
                "type": "object",
                "properties": {
                    "VendorName": {"type": ["string", "null"]},
                    "CustomerName": {"type": ["string", "null"],
                                        "enum": socs},
                    "CustomerTaxId": {"type": ["string", "null"],
                                        "enum": cuits},
                    "CustomerCodSap": {"type": ["string", "null"],
                                        "enum": cods_soc},
                    "VendorTaxId": {"type": ["string", "null"]},
                    "CustomerAddress": {"type": ["string", "null"]},
                    "InvoiceId": {
                        "type": ["array", "null"],
                        "items": {"type": "string"}
                    },
                    "InvoiceDate": {
                        "type": ["array", "null"],
                        "items": {"type": "string"}
                    },
                    "InvoiceTotal": {"type": ["string", "null"]},
                    "PurchaseOrderNumber": {"type": ["string", "null"]},
                    "Signed": {"type": "boolean"}
                },
                "required": [
                    "VendorName", "CustomerName", "CustomerTaxId", "CustomerCodSap", 
                    "VendorTaxId", "CustomerAddress", "InvoiceId", "InvoiceDate", 
                    "InvoiceTotal", "PurchaseOrderNumber", "Signed"
                ],
                "additionalProperties": False
            }
        },
        "required": ["final_answer"],
        "additionalProperties": False
    },
    "strict": True
}

def find_missing_fields(data):
    """
    Busca recursivamente una clave llamada 'missing_fields' dentro de una estructura arbitraria 
    de listas y diccionarios, y devuelve todas las listas encontradas.
    
    :param data: Puede ser un dict o list con estructuras anidadas desconocidas.
    :return: Lista con todos los valores encontrados bajo la clave 'missing_fields'.
    """
    results = []

    if isinstance(data, dict):
        for key, value in data.items():
            if key == "missing_fields" and isinstance(value, list):
                results.append(value)
            else:
                results.extend(find_missing_fields(value))

    elif isinstance(data, list):
        for item in data:
            results.extend(find_missing_fields(item))

    return results

class ResultExtraction(TypedDict):
    fuente:Annotated[str, ...]
    valores:Annotated[list, ...]

class OutputState(TypedDict):
    extractions:Annotated[list, ...]
    tokens:Annotated[int, ...]

merger = merger_definition | llm4o.with_structured_output(ResultExtraction)

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    tokens:Annotated[int, operator.add]
    text: str   # Almacena asunto y cuerpo del mail
    images: list  # Almacena las imagenes adjuntas
    pdfs: list  # Almacena los pdfs adjuntos

class Fields(TypedDict):
    CustomerName:str
    CustomerTaxId: str
    CustomerCodSap: str
    InvoiceId:list
    VendorName: str
    VendorTaxId: str
    PurchaseOrderNumber:list
    InvoiceDate:list
    InvoiceTotal:list




def asignar_codigo_sap(datos_facturas, empresas):
    """
    Agrega el 'Código SAP' a cada factura si encuentra coincidencia en 'CustomerName' o 'CustomerTaxId'.
    
    :param datos_facturas: Lista de diccionarios con datos de facturas.
    :param empresas: Lista de diccionarios con datos de empresas.
    :return: Lista de facturas con 'Código SAP' agregado si aplica.
    """
    for factura in datos_facturas:
        customer_name = factura.get("CustomerName", "").strip().lower()
        customer_tax_id = factura.get("CustomerTaxId", "").strip()
        
        for empresa in empresas:
            empresa_name = empresa.get("CustomerName", "").strip().lower()
            empresa_tax_id = empresa.get("CustomerTaxId", "").strip()
            
            if customer_tax_id and customer_tax_id == empresa_tax_id:
                factura["Código SAP"] = empresa["Código SAP"]
                break
            elif customer_name and customer_name == empresa_name:
                factura["Código SAP"] = empresa["Código SAP"]
                break
    
    return datos_facturas

class ClassifyNode:
    def __call__(self, state:InputSchema) -> State:
        try:
            image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
            pdf_extension = (".pdf")
            images, pdfs = [], []
            files = state["adjuntos"]
            attachments_names = []
            for file in files:
                file_name = file.get("file_name", "").lower()
                attachments_names.append(file_name)
                if file_name.endswith(image_extensions):
                    images.append(file)
                elif file_name.endswith(pdf_extension):
                    pdfs.append(file)
            return {
                "images": images, 
                "pdfs": pdfs, 
                "text": f"""{"asunto: " + state["asunto"] + " cuerpo: " + state["cuerpo"] + " adjuntos: " + "".join(attachments_names)}""", 
                "tokens":0
            }
        except Exception as e:
            logger.error(f"Error en 'ClassifyNode': {str(e)}")
            raise

class VisionNode:
    async def __call__(self, state: State) -> State:
        print(f"DEBUG-VisionNode")
        try:
            images_from_pdfs = []
            for file in state["pdfs"]:
                content = file.get("content", b"")
                pages = pdf_binary_to_images_base64(content, dpi=300)
                for page in pages:
                    image = {
                        "file_name": file["file_name"],
                        "content": page["content"]
                    }
                    images_from_pdfs.append(image)
            extractor = ImageFieldExtractor()
            result = extractor.extract_fields(base64_images=images_from_pdfs, fields_to_extract=fields_to_extract, restrictions=lista_sociedades)
            tokens = 0
            print(f"Resultado de extraccion: \n{result}")
            return {"tokens": state["tokens"] + tokens, "aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'VisionNode': {str(e)}")
            raise

class ImageNode:
    async def __call__(self, state: State) -> State:
        print(f"DEBUG-ImageNode")
        try:
            images_b64 = []
            for image in state["images"]:
                content = image.get("content", b"")
                image64 = {
                    "file_name": image["file_name"],
                    "content": base64.b64encode(content).decode('utf-8')
                }
                images_b64.append(image64)

            extractor = ImageFieldExtractor()
            result = extractor.extract_fields(base64_images=images_b64, fields_to_extract=fields_to_extract, restrictions=lista_sociedades)
            tokens = 0
            return {"tokens": state["tokens"] + tokens, "aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'ImageNode': {str(e)}")
            raise


class PrebuiltNode:
    async def __call__(self, state: State) -> State:
        print(f"DEBUG-Prebuilt")
        try:
            result = process_binary_files(binary_files=state["pdfs"], fields_to_extract=fields_to_extract)
            result = asignar_codigo_sap(result, lista_sociedades)
            print(f"DEBUG-Resultado Prebuilt: \n{result}")
            return {"tokens": 0, "aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'PrebuiltNode': {str(e)}")
            raise


class NamesAndCuitsNode:
    async def __call__(self, state: State) -> Fields:
        print(f"DEBUG-NamesCuitsNode")
        try:
            prompt = [
                {"role": "system", 
                 "content": TextExtractorPrompt.names_and_cuits_prompt},
                 {"role": "user",
                  "content": f"Dado el siguiente texto de un mail extrae el dato pedido: {state['text']}"}
            ]
            result = llm4o.generate(
                messages=[prompt], 
                response_format={
                "type": "json_schema",
                "json_schema": json_schema_names
                }
            )
            result = json.loads(result.generations[0][0].text.strip())["final_answer"]
            return {"CustomerName": result["CustomerName"], "CustomerTaxId": result["CustomerTaxId"], "VendorName": result["VendorName"], "VendorTaxId": result["VendorTaxId"]}
        except Exception as e:
            logger.error(f"Error en 'NamesAndCuitsNode': {str(e)}")
            raise

class InvoiceNode:
    async def __call__(self, state:State) -> Fields:
        print(f"DEBUG-InvoiceNode")
        try:
            prompt = [
                {"role": "system", 
                 "content": TextExtractorPrompt.invoice_id_prompt},
                 {"role": "user",
                  "content": f"Dado el siguiente texto de un mail extrae los datos pedidos: {state['text']}"}
            ]
            result = llm4o.generate(
                messages=[prompt], 
                response_format={
                "type": "json_schema",
                "json_schema": json_schema_invoices
                }
            )
            result = json.loads(result.generations[0][0].text.strip())["final_answer"]
            return {"InvoiceId": result["InvoiceId"], "InvoiceDate": result["InvoiceDate"], "InvoiceTotal": result["InvoiceTotal"], "PurchaseOrderNumber": result["PurchaseOrderNumber"]}
        except Exception as e:
            logger.error(f"Error en 'InvoiceNode': {str(e)}")
            raise

def MergeFieldsNode(state: Fields) -> State:
    print(f"DEBUG-MergeFields")
    try:
        # state = fix_data(state)
        missing_fields = []
        for field in fields_to_extract:
            if field not in state:
                missing_fields.append(field)
        result = {
            "Mail":[{
                "page_number": 1,
                "fields":state, 
                "missing_fields":missing_fields, 
                "error":"",
                "source": "Mail"
            }],
        }
        return {"aggregate": [result]}
    except Exception as e:
        logger.error(f"Error en 'MergeFieldsNode': {str(e)}")
        raise

# Analizo todo los adjuntos si los hay
def router(state: State) -> Sequence[str]:
    print(f"DEBUG-Router")
    try:
        routes = []

        routes.append("extract names and cuits")
        routes.append("extract invoices IDs")
        
        if state["images"]:
            routes.append("extract from images")
        
        if state["pdfs"]:
            routes.append("extract with prebuilt")
            routes.append("extract with vision")

        if len(routes) == 0:
            return ["merger"]
        
        return routes
    except Exception as e:
        logger.error(f"Error en 'router': {str(e)}")
        raise

async def super_steps_balance(state: State):
    print("DEBUG-SSB")
    return state

async def merge_results(state: State) -> OutputState:
    print(f"DEBUG-Merger")
    try:
        grouped_data = defaultdict(lambda: {"extractions": defaultdict(list)})
        for extraction in state["aggregate"]:
            for file_name, data_list in extraction.items():
                for data in data_list:
                    source = data.get("source", "Unknown")  #Se obtiene la fuente
                    grouped_data[source]["extractions"][file_name].append({
                        "extraction_number": data.get("extraction_number"),
                        "fields": data.get("fields", {}),
                        "missing_fields": data.get("missing_fields", []),
                        "tokens": data.get("tokens", 0)
                    })

        #Reformateo para cumplir con la estructura deseada
        formatted_data = [
            {
                "source": src,
                "extractions": [{file_name: extractions} for file_name, extractions in values["extractions"].items()]
            }
            for src, values in grouped_data.items()
        ]

        return {"extractions": formatted_data, "tokens": state["tokens"]}

    except Exception as e:
        logger.error(f"Error en 'merge_results': {str(e)}")
        raise

def should_continue(state:State):
    print(f"DEBUG-SC")
    try:
        return END
    except Exception as e:
        logger.error(f"Error en 'should_continue': {str(e)}")
        raise

# Construcción del grafo
builder = StateGraph(State, input=InputSchema, output=OutputState)

builder.add_node("initializer", ClassifyNode())
builder.add_node("extract names and cuits", NamesAndCuitsNode())
builder.add_node("extract invoices IDs", InvoiceNode())
builder.add_node("merge fields", MergeFieldsNode)
builder.add_node("extract from images", ImageNode())
builder.add_node("extract with vision", VisionNode())
builder.add_node("extract with prebuilt", PrebuiltNode())
builder.add_node("merger", merge_results)
builder.add_node("SSB", super_steps_balance)

builder.add_edge(START, "initializer")
builder.add_conditional_edges("initializer", router, ["extract names and cuits", "extract invoices IDs", "extract with prebuilt", "extract from images", "extract with vision", "SSB"])
builder.add_edge("extract invoices IDs", "merge fields")
builder.add_edge("extract names and cuits", "merge fields")
# builder.add_conditional_edges("extract with prebuilt", should_continue, {"vision":"extract with vision", END:"merger"})
builder.add_edge("extract with prebuilt", "SSB")
builder.add_edge("extract from images", "SSB")
builder.add_edge("extract with vision", "SSB")
builder.add_edge("merge fields", "merger")
builder.add_edge("SSB", "merger")
builder.add_edge("merger", END)

extractor = builder.compile()
