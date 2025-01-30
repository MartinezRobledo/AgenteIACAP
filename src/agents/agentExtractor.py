import operator
import json
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage
from src.services.tools.document_intelligence import process_base64_files, ImageFieldExtractor
from typing import Annotated, Any, Sequence
from langgraph.graph import StateGraph, START, END
from src.configs.classes import Input
from src.configs.llms import llm4o
from src.configs.Prompt_Template import text_extractor_definition, fields_to_extract

text_extractor = text_extractor_definition | llm4o

class State(TypedDict):
    # La lista `aggregate` acumulará valores
    aggregate: Annotated[list, operator.add]
    text: str   # Almacena asunto y cuerpo del mail
    images: list  # Almacena las imagenes adjuntas
    pdfs: list  # Almacena los pdfs adjuntos
    others: list   # Almacena el resto de adjuntos
    input_value: Input  # Valor recibido desde START

class OutputState(TypedDict):
    extractions:dict

class ClassifyNode:
    def __call__(self, state:State) -> Any:
        # "a" pasa valores distintos a "b" y "c"
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
        pdf_extension = (".pdf")
        images, pdfs, others = [], [], []
        files = state["input_value"]["adjuntos"]
        for file in files:
            file_name = file.get("file_name", "").lower()
            if file_name.endswith(image_extensions):
                images.append(file)
            elif file_name.endswith(pdf_extension):
                pdfs.append(file)
            else:
                others.append(others)

        print("Clasificación completada.")
        return {"images": images, "pdfs": pdfs, "others": others, "text": state["input_value"]["asunto"] + state["input_value"]["cuerpo"]}


class ImageNode:
    async def __call__(self, state: State) -> Any:
        # "b" retorna lo que recibió de "a"
        # extractor = ImageFieldExtractor()
        # result = extractor.extract_fields(base64_images=state["images"], fields_to_extract=fields_to_extract)
        result = process_base64_files(base64_files=state["images"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}



class PdfNode:
    async def __call__(self, state: State) -> Any:
        # "c" retorna lo que recibió de "a"
        result = process_base64_files(base64_files=state["pdfs"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}

class TextNode:
    async def __call__(self, state: State) -> State:
        # "c" retorna lo que recibió de "a"
        prompt = HumanMessage(
            content=f"""**Contenido del correo:**
                    {state["text"]}
                    """
                    # Devuélveme únicamente el JSON con los datos pedidos, sin explicaciones adicionales.
        )
        result = await text_extractor.ainvoke({"messages": [prompt]})
        content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
        data = json.loads(content)
        return {"aggregate": [content]}

# Fuerzo la salida a Merger
def router(state:State) -> Sequence[str]:
    return ["merger"]

def merge_results(state: State) -> OutputState:
    """
    Combina los resultados de imágenes y archivos en un único diccionario de extracciones.
    """
    print("Fusionando resultados...")
    return {"extractions": state["aggregate"]}


# Construcción del grafo
builder = StateGraph(input=State, output=OutputState)

# Nodo Inicializador: Determina todos los tipos de datos que se tienen a la entrada de datos
# y lo asigna a cada campo del estado correspondiente
builder.add_node("initializer", ClassifyNode())
builder.add_edge(START, "initializer")

# Nodo de extracción de texto: Extrae toda la información relevante del texto del mail
builder.add_node("extract from text", TextNode())
builder.add_edge("initializer", "extract from text")

# Nodo Router: En base a la información obtenida determina la ruta a seguir
# Si la información es suficiente va directo al merger
# Si es necesario el proceso de adjuntos los dispara en paralelo
builder.add_conditional_edges("extract from text", router, ["extract from images", "extract from pdf", "merger"])

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