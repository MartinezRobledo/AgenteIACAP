import operator
import json
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from src.services.tools.document_intelligence import process_base64_files, ImageFieldExtractor
from typing import Annotated, Any, Sequence
from langgraph.graph import StateGraph, START, END
from src.configs.classes import Input
from src.configs.llms import llm4o
from src.configs.Prompt_Template import TextExtractorPrompt, fields_to_extract
from src.services.tools.validar_datos import validate_invoice

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    text: str   # Almacena asunto y cuerpo del mail
    images: list  # Almacena las imagenes adjuntas
    pdfs: list  # Almacena los pdfs adjuntos
    others: list   # Almacena el resto de adjuntos

class OutputState(TypedDict):
    extractions:dict

class Fields(TypedDict):
    customer_name:str
    customer_tax_id:str
    invoice_id:str
    vendor_tax_id:str

class ClassifyNode:
    def __call__(self, state:Input) -> State:
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
        pdf_extension = (".pdf")
        images, pdfs, others = [], [], []
        files = state["adjuntos"]
        for file in files:
            file_name = file.get("file_name", "").lower()
            if file_name.endswith(image_extensions):
                images.append(file)
            elif file_name.endswith(pdf_extension):
                pdfs.append(file)
            else:
                others.append(others)
        return {"images": images, "pdfs": pdfs, "others": others, "text": str(state["asunto"]) + str(state["cuerpo"])}


class ImageNode:
    async def __call__(self, state: State) -> Any:
        # extractor = ImageFieldExtractor()
        # result = extractor.extract_fields(base64_images=state["images"], fields_to_extract=fields_to_extract)
        result = process_base64_files(base64_files=state["images"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}

class PdfNode:
    async def __call__(self, state: State) -> Any:
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
        prompt = [SystemMessage(content=TextExtractorPrompt.invoice_id_prompt)] + [HumanMessage(content=f"Dado el siguiente texto de un mail extrae el dato pedido: {state['text']}")]

        result = await llm4o.ainvoke(prompt)
        content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
        return {"invoice_id": content}

class MergeFieldsNode:
    async def __call__(self, state: Fields) -> State:
        missing_fields = fields_to_extract
        merge = {"fields":state, "missing_fields":[], "error":""}
        return {"aggregate": [merge]}

# Fuerzo la salida a Merger
def router(state:State) -> Sequence[str]:
    return ["merger"]

def merge_results(state: State) -> OutputState:
    """
    Combina los resultados de imágenes y archivos en un único diccionario de extracciones.
    """
    return {"extractions": state["aggregate"]}


# Construcción del grafo
builder = StateGraph(State, input=Input, output=OutputState)

# Nodo Inicializador: Determina todos los tipos de datos que se tienen a la entrada de datos
# y lo asigna a cada campo del estado correspondiente
builder.add_node("initializer", ClassifyNode())
builder.add_edge(START, "initializer")

builder.add_node("extract names and cuits", NamesAndCuitsNode())
builder.add_node("extract invoices IDs", InvoiceNode())
builder.add_edge("initializer", "extract names and cuits")
builder.add_edge("initializer", "extract invoices IDs")

# Nodo de extracción de texto: Extrae toda la información relevante del texto del mail
builder.add_node("merge fields", MergeFieldsNode())
builder.add_edge("extract names and cuits", "merge fields")
builder.add_edge("extract invoices IDs", "merge fields")

# Nodo Router: En base a la información obtenida determina la ruta a seguir
# Si la información es suficiente va directo al merger
# Si es necesario el proceso de adjuntos los dispara en paralelo
builder.add_conditional_edges("merge fields", router, ["extract from images", "extract from pdf", "merger"])

# Nodo Imagen: Extraer datos de imagen
builder.add_node("extract from images", ImageNode())

# Nodo PDF: Extraer datos de pdf
builder.add_node("extract from pdf", PdfNode())

# Nodo Merger: Fusionar resultados
builder.add_node("merger", merge_results)
builder.add_edge("extract from images", "merger")
builder.add_edge("extract from pdf", "merger")
builder.add_edge("merger", END)

extractor = builder.compile()