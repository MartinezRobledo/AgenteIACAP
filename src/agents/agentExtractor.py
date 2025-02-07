from collections import defaultdict
import operator
import json
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from src.services.tools.document_intelligence import process_base64_files, ImageFieldExtractor
from typing import Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from src.configs.classes import Input
from src.configs.llms import llm4o
from src.configs.Prompt_Template import TextExtractorPrompt, fields_to_extract, merger_definition
from src.services.tools.convert_pdf import pdf_base64_to_image_base64
import textwrap

def print_truncated(data, max_length=50, indent=0):
    """Imprime un diccionario truncando los strings largos sin modificar los datos originales."""
    if isinstance(data, dict):
        for key, value in data.items():
            print(" " * indent + str(key) + ":")
            print_truncated(value, max_length, indent + 2)
    elif isinstance(data, list):
        for item in data:
            print_truncated(item, max_length, indent)
    elif isinstance(data, str):
        print(" " * indent + textwrap.shorten(data, width=max_length, placeholder="..."))
    else:
        print(" " * indent + str(data))

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
    def __call__(self, state:Input) -> State:
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
        pdf_extension = (".pdf")
        images, pdfs = [], []
        files = state["adjuntos"]
        for file in files:
            file_name = file.get("file_name", "").lower()
            if file_name.endswith(image_extensions):
                print(f"DEBUG - Clasificando como imagen: {file_name}")
                images.append(file)
            elif file_name.endswith(pdf_extension):
                print(f"DEBUG - Clasificando como PDF: {file_name}")
                pdfs.append(file)

        return {"images": images, "pdfs": pdfs, "text": str(state["asunto"]) + str(state["cuerpo"]), "tokens":0}


class VisionNode:
    async def __call__(self, state: State) -> State:
        images_from_pdfs = []
        for file in state["pdfs"]:
            pages = pdf_base64_to_image_base64(file["base64_content"], 1)
            for page in pages:
                image = {
                    "file_name": file["file_name"],
                    "base64_content": page
                }
                images_from_pdfs.append(image)
        extractor = ImageFieldExtractor()
        result = extractor.extract_fields(base64_images=state["images"]+images_from_pdfs, fields_to_extract=fields_to_extract)
        tokens = 0
        for element in result:
            tokens += int(result[element]["tokens"])
        print(f"DEBUG - Extraccion de Vision: {result}")
        return {"tokens": state["tokens"] + tokens, "aggregate": [result]}

class ImageNode:
    async def __call__(self, state: State) -> State:
        extractor = ImageFieldExtractor()
        result = extractor.extract_fields(base64_images=state["images"], fields_to_extract=fields_to_extract)
        tokens = 0
        for element in result:
            tokens += int(result[element]["tokens"])
        print(f"DEBUG - Extraccion de imagenes: {result}")
        return {"tokens": state["tokens"] + tokens, "aggregate": [result]}

class PrebuiltNode():
    async def __call__(self, state: State) -> State:
        result = process_base64_files(base64_files=state["pdfs"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}

class NamesAndCuitsNode:
    async def __call__(self, state:State) -> Fields:
        prompt = [SystemMessage(content=TextExtractorPrompt.names_and_cuits_prompt)] + [HumanMessage(content=f"Dado el siguiente texto de un mail extrae el dato pedido: {state['text']}")]
        result = await llm4o.ainvoke(prompt)
        content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
        data = json.loads(content)
        return {"customer_name": data["CustomerName"], "customer_tax_id": data["CustomerTaxId"], "vendor_tax_id": data["VendorTaxId"]}
    
class InvoiceNode:
    async def __call__(self, state:State) -> Fields:
        prompt = [SystemMessage(content=TextExtractorPrompt.invoice_id_prompt)] + [HumanMessage(content=f"Dado el siguiente texto de un mail extrae los datos pedidos: {state['text']}")]
        result = await llm4o.ainvoke(prompt)
        content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
        content = json.loads(content)
        print(f"Invoice data: {content}")
        return {"invoice_id": content["InvoiceId"], "invoice_date": content["InvoiceDate"], "invoice_total": content["InvoiceTotal"]}

class MergeFieldsNode:
    async def __call__(self, state: Fields) -> State:
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
        # Mantenemos el estado original y solo agregamos "aggregate"
        return {"aggregate": [result]}

# Analizo todo los adjuntos si los hay
def router(state: State) -> Sequence[str]:
    routes = []
    if state["images"]:
        print("DEBUG - router GO TO vision")
        routes.append("extract from images")
    
    if state["pdfs"]:
        print("DEBUG - router GO TO prebuilt")
        routes.append("extract with prebuilt")

    if len(routes) == 0:
        print("DEBUG - router GO TO merger")
        return ["merger"]
    
    return routes

def merge_results(state: State) -> OutputState:
    # Resultado de agrupación
    grouped_data = defaultdict(list)

    # Procesar los datos
    for item in state["aggregate"]:
        if isinstance(item, list):  # Caso: Lista de documentos
            print("instancia de lista")
            for doc in item:
                source = doc['source']
                grouped_data[source].append(doc)
        elif isinstance(item, dict):  # Caso: Diccionario de archivos
            print("instancia de diccionario")
            for key, value in item.items():
                source = value['source']
                # Eliminar el campo 'source'
                value.pop('source', None)
                grouped_data[source].append(value)

    # Formatear la salida
    formatted_data = []
    for source, values in grouped_data.items():
        formatted_data.append({
            'fuente': source,
            'valores': values
        })
    return {"extractions":formatted_data, "tokens":state["tokens"]}

def should_continue(state:State):
    print("DEBUG - GO TO Vision Node")
    return "vision"

# Construcción del grafo
builder = StateGraph(State, input=Input, output=OutputState)

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