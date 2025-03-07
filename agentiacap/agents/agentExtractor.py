import base64
import operator
import json
import logging
from collections import defaultdict
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from agentiacap.tools.document_intelligence import ImageFieldExtractor, process_binary_files, find_in_binary_files_layout
from agentiacap.utils.globals import InputSchema, fields_to_extract_rpa
from agentiacap.llms.llms import llm4o
from agentiacap.llms.Prompts import TextExtractorPrompt, fields_to_extract, merger_definition 
from agentiacap.tools.convert_pdf import pdf_binary_to_images_base64

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
    CustomerTaxId:str
    InvoiceId:str
    VendorTaxId:str
    PurchaseOrderNumber:str
    InvoiceDate:str
    InvoiceTotal:str


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
                pages = pdf_binary_to_images_base64(file["content"], dpi=300)
                for page in pages:
                    image = {
                        "file_name": file["file_name"],
                        "content": page["content"]
                    }
                    images_from_pdfs.append(image)
            extractor = ImageFieldExtractor()
            result = extractor.extract_fields(base64_images=images_from_pdfs, fields_to_extract=fields_to_extract)
            tokens = 0
            print(f"Resultado de extraccion: \n{result}")
            return {"tokens": state["tokens"] + tokens, "aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'VisionNode': {str(e)}")
            raise

class ImageNode:
    async def __call__(self, state: State) -> State:
        try:
            images_b64 = []
            for image in state["images"]:
                image64 = {
                    "file_name": image["file_name"],
                    "content": base64.b64encode(image["content"]).decode('utf-8')
                }
                images_b64.append(image64)

            extractor = ImageFieldExtractor()
            result = extractor.extract_fields(base64_images=images_b64, fields_to_extract=fields_to_extract)
            print(f"Resultado de extraccion: \n{result}")
            tokens = 0
            return {"tokens": state["tokens"] + tokens, "aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'ImageNode': {str(e)}")
            raise


class PrebuiltNode():
    async def __call__(self, state: State) -> State:
        try:
            result = process_binary_files(binary_files=state["pdfs"], fields_to_extract=fields_to_extract)
            print(f"Resultado de prebuilt: \n{result}")
            return {"aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'PrebuiltNode': {str(e)}")
            raise

class PrebuiltLayoutNode():
    async def __call__(self, state: State, inputs: list) -> State:
        try:
            result = []
            for data in inputs:
                invoice, date = data.get("invoice", ""), data.get("date", "")
                user_text_prompt = f"""Extrae los datos de la tabla siguiendo estos pasos:
                **Aclaración: Solo se debe ejecutar el flujo alternativo si el flujo principal lo solicita explícitamente.
                **Flujo principal (obligatorio):
                    - Busca en la columna "Referencia" el numero de factura: {invoice}. Si no encontras la factura intenta el flujo alternativo.
                    - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp." y obtene 'due_date' de la columna "Vence El". Si no encontras el numero retorna en este punto.
                    - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
                    - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'purchase_number' y el la fecha 'op_date' de la columna "Fecha doc.".
                **Flujo alternativo (Opcional):
                    - Busca en la columna "Fecha doc." la fecha: {date}. Si no encontras la fecha retorna.
                    - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp." y obtene 'due_date' de la columna "Vence El". Si no encontras el numero retorna en este punto.
                    - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
                    - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'op' y el la fecha 'op_date' de la columna "Fecha doc.".
                **Retorno:
                    - Se debe devolver unicamente los datos que se conocen.
                    - Los datos que no se encontraron se deben indicar como un string vacío.
                    - El campo found es un bool que indica si se encontró o no el numero de 10 digitos correspondiente a purchase_number.
                    - El campo overdue es un bool que indica si la fecha actual es mayor a la fecha de vencimeinto que corresponde al campo due_date."""
                result += find_in_binary_files_layout(binary_files=state["pdfs"], fields_to_extract=fields_to_extract_rpa, mothod_prompt=user_text_prompt)
            return {"aggregate": result}
        except Exception as e:
            logger.error(f"Error en 'PrebuiltLayoutNode': {str(e)}")
            raise

class NamesAndCuitsNode:
    async def __call__(self, state: State) -> Fields:
        try:
            prompt = [SystemMessage(content=TextExtractorPrompt.names_and_cuits_prompt)] + [HumanMessage(content=f"Dado el siguiente texto de un mail extrae el dato pedido: {state['text']}")]
            result = await llm4o.ainvoke(prompt)
            content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
            data = json.loads(content)
            return {"CustomerName": data["CustomerName"], "CustomerTaxId": data["CustomerTaxId"], "VendorTaxId": data["VendorTaxId"]}
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
            return {"InvoiceId": content["InvoiceId"], "InvoiceDate": content["InvoiceDate"], "InvoiceTotal": content["InvoiceTotal"]}
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
                "Mail":[{
                    "page_number": 1,
                    "fields":state, 
                    "missing_fields":missing_fields, 
                    "error":"",
                    "source": "Mail"
                }],
            }
            print(f"Salida de Text extractor: {result}")
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
            routes.append("extract with vision")

        if len(routes) == 0:
            return ["merger"]
        
        return routes
    except Exception as e:
        logger.error(f"Error en 'router': {str(e)}")
        raise

async def merge_results(state: State) -> OutputState:
    try:
        grouped_data = defaultdict(lambda: {"extractions": defaultdict(list)})
        print(f"Ingreso de datos Merge: \n{state['aggregate']}")
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
builder.add_conditional_edges("initializer", router, ["extract with prebuilt", "extract from images", "extract with vision", "merger"])
builder.add_conditional_edges("extract with prebuilt", should_continue, {"vision":"extract with vision", END:"merger"})
builder.add_edge("extract from images", "merger")
builder.add_edge(["extract with vision", "merge fields"], "merger")
builder.add_edge("merge fields", "merger")
builder.add_edge("merger", END)

extractor = builder.compile()
