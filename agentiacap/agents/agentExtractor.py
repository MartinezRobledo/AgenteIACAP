import operator
import json
import logging
from collections import defaultdict
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from agentiacap.tools.document_intelligence import process_base64_files, ImageFieldExtractor, process_binary_files
from agentiacap.utils.globals import InputSchema
from agentiacap.llms.llms import llm4o
from agentiacap.llms.Prompts import TextExtractorPrompt, fields_to_extract, merger_definition
from agentiacap.tools.convert_pdf import pdf_base64_to_image_base64, pdf_binary_to_images

# Configuración del logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

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
    extractions:Annotated[list, operator.add]
    tokens:Annotated[int, ...]

merger = merger_definition | llm4o.with_structured_output(ResultExtraction)

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    tokens: int
    text: str   # Almacena asunto y cuerpo del mail
    images: list  # Almacena las imagenes adjuntas
    pdfs: list  # Almacena los pdfs adjuntos

class Fields(TypedDict):
    customer_name:str
    customer_tax_id:str
    invoice_id:str
    vendor_tax_id:str
    purchase_order_number:str
    invoice_date:str
    invoice_total:str


class ClassifyNode:
    def __call__(self, state:InputSchema) -> State:
        try:
            image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
            pdf_extension = (".pdf")
            images, pdfs = [], []
            files = state["adjuntos"]
            for file in files:
                file_name = file.get("file_name", "").lower()
                if file_name.endswith(image_extensions):
                    images.append(file)
                elif file_name.endswith(pdf_extension):
                    pdfs.append(file)
            return {"images": images, "pdfs": pdfs, "text": str(state["asunto"]) + str(state["cuerpo"]), "tokens":0}
        except Exception as e:
            logger.error(f"Error en 'ClassifyNode': {str(e)}")
            raise

class VisionNode:
    async def __call__(self, state: State) -> State:
        try:
            images_from_pdfs = []
            for file in state["pdfs"]:
                pages = pdf_binary_to_images(file["content"], 1)
                for page in pages:
                    image = {
                        "file_name": file["file_name"],
                        "content": page
                    }
                    images_from_pdfs.append(image)
            extractor = ImageFieldExtractor()
            result = extractor.extract_fields_binary(base64_images=state["images"]+images_from_pdfs, fields_to_extract=fields_to_extract)
            print("DEBUG - Resultado de vision: ", result)
            tokens = 0
            for element in result:
                tokens += int(result[element]["tokens"])
            return {"tokens": state["tokens"] + tokens, "aggregate": [result]}
        except Exception as e:
            logger.error(f"Error en 'VisionNode': {str(e)}")
            raise

class ImageNode:
    async def __call__(self, state: State) -> State:
        try:
            extractor = ImageFieldExtractor()
            result = extractor.extract_fields_binary(base64_images=state["images"], fields_to_extract=fields_to_extract)
            tokens = 0
            for element in result:
                tokens += int(result[element]["tokens"])
            print("DEBUG - Resultado de vision: ", result)
            return {"tokens": state["tokens"] + tokens, "aggregate": [result]}
        except Exception as e:
            logger.error(f"Error en 'ImageNode': {str(e)}")
            raise

class PrebuiltNode():
    async def __call__(self, state: State) -> State:
        try:
            result = process_binary_files(base64_files=state["pdfs"], fields_to_extract=fields_to_extract)
            return {"aggregate": [result]}
        except Exception as e:
            logger.error(f"Error en 'PrebuiltNode': {str(e)}")
            raise

class NamesAndCuitsNode:
    async def __call__(self, state: State) -> Fields:
        try:
            prompt = [SystemMessage(content=TextExtractorPrompt.names_and_cuits_prompt)] + [HumanMessage(content=f"Dado el siguiente texto de un mail extrae el dato pedido: {state['text']}")]
            result = await llm4o.ainvoke(prompt)
            content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
            data = json.loads(content)
            return {"customer_name": data["CustomerName"], "customer_tax_id": data["CustomerTaxId"], "vendor_tax_id": data["VendorTaxId"]}
        except Exception as e:
            logger.error(f"Error en 'NamesAndCuitsNode': {str(e)}")
            raise

class InvoiceNode:
    async def __call__(self, state:State) -> Fields:
        try:
            prompt = [SystemMessage(content=TextExtractorPrompt.invoice_id_prompt)] + [HumanMessage(content=f"Dado el siguiente texto de un mail extrae los datos pedidos: {state['text']}")]
            result = await llm4o.ainvoke(prompt)
            content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
            content = json.loads(content)
            return {"invoice_id": content["InvoiceId"], "invoice_date": content["InvoiceDate"], "invoice_total": content["InvoiceTotal"]}
        except Exception as e:
            logger.error(f"Error en 'InvoiceNode': {str(e)}")
            raise

class MergeFieldsNode:
    async def __call__(self, state: Fields) -> State:
        try:
            missing_fields = []
            for field in fields_to_extract:
                if field not in state:
                    missing_fields.append(field)
            result = {
                "Mail":{
                    "page_number": 1,
                    "fields":state, 
                    "missing_fields":missing_fields, 
                    "error":"",
                    "source": "Mail"
                },
            }
            return {"aggregate": [result]}
        except Exception as e:
            logger.error(f"Error en 'MergeFieldsNode': {str(e)}")
            raise

# Analizo todo los adjuntos si los hay
def router(state: State) -> Sequence[str]:
    try:
        routes = []
        if state["images"]:
            routes.append("extract from images")
        
        if state["pdfs"]:
            routes.append("extract with prebuilt")

        if len(routes) == 0:
            return ["merger"]
        
        return routes
    except Exception as e:
        logger.error(f"Error en 'router': {str(e)}")
        raise

def merge_results(state: State) -> OutputState:
    try:
        grouped_data = defaultdict(list)

        for item in state["aggregate"]:
            item = item[0]  # Extraer el diccionario dentro de la lista
            print("DEBUG - Merger Item: ", item)
            for key, value in item.items():  # Usar .items() para obtener clave y valor correctamente
                    source = value.get('source') if isinstance(value, dict) else None
                    if source:
                        value.pop('source')
                        grouped_data[source].append({key: value})

        formatted_data = [{'fuente': source, 'valores': values} for source, values in grouped_data.items()]

        # formatted_data = []
        # for source, values in grouped_data.items():
        #     formatted_data.append({
        #         'fuente': source,
        #         'valores': values
        #     })
        print("DEBUG - Merger result: ", formatted_data)
        return {"extractions":formatted_data, "tokens":state["tokens"]}
    except Exception as e:
        logger.error(f"Error en 'merge_results': {e}")
        raise

def should_continue(state:State):
    try:
        return "vision"
    except Exception as e:
        logger.error(f"Error en 'should_continue': {str(e)}")
        raise

# Construcción del grafo
builder = StateGraph(State, input=InputSchema, output=OutputState)

builder.add_node("initializer", ClassifyNode())
builder.add_node("extract names and cuits", NamesAndCuitsNode())
builder.add_node("extract invoices IDs", InvoiceNode())
builder.add_node("merge fields", MergeFieldsNode())
builder.add_node("extract from images", ImageNode())
builder.add_node("extract with vision", VisionNode())
builder.add_node("extract with prebuilt", PrebuiltNode())
builder.add_node("merger", merge_results)

builder.add_edge(START, "initializer")
builder.add_edge("initializer", "extract names and cuits")
builder.add_edge("initializer", "extract invoices IDs")
builder.add_edge("extract invoices IDs", "merge fields")
builder.add_edge("extract names and cuits", "merge fields")
builder.add_conditional_edges("initializer", router, ["extract with prebuilt", "extract from images", "merger"])
builder.add_conditional_edges("extract with prebuilt", should_continue, {"vision":"extract with vision", END:"merger"})
builder.add_edge("extract from images", "merger")
builder.add_edge("extract with vision", "merger")
builder.add_edge("merge fields", "merger")
builder.add_edge("merger", END)

extractor = builder.compile()
