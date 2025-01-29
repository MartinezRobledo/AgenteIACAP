import asyncio
import operator
from tabulate import tabulate
from typing_extensions import TypedDict
from src.services.tools.document_intelligence import process_base64_files, ImageFieldExtractor
from src.utils.armar_json_adjuntos_b64 import generate_json_from_file
from typing import Annotated, Any, List, Dict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # La lista `aggregate` acumulará valores
    aggregate: Annotated[list, operator.add]
    images: list  # Almacena el valor para "b"
    files: list  # Almacena el valor para "c"
    input_value: list  # Valor recibido desde START

class OutputState(TypedDict):
    extractions:dict

fields_to_extract = [
    "VendorName",
    "CustomerName",
    "CustomerTaxId",
    "VendorTaxId",
    "CustomerAddress",
    "InvoiceId",
    "InvoiceDate",
    "InvoiceTotal",
]

class ClassifyNode:
    def __call__(self, state:State) -> Any:
        # "a" pasa valores distintos a "b" y "c"
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
        images, others = [], []
        files = state["input_value"]
        for file in files:
            file_name = file.get("file_name", "").lower()
            if file_name.endswith(image_extensions):
                images.append(file)
            else:
                others.append(file)

        print("Clasificación completada.")
        value_for_images = images
        value_for_pdfs = others
        return {"images": value_for_images, "files": value_for_pdfs}


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
        result = process_base64_files(base64_files=state["files"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}


def merge_results(state: State) -> OutputState:
    """
    Combina los resultados de imágenes y archivos en un único diccionario de extracciones.
    """
    print("Fusionando resultados...")
    return {"extractions": state["aggregate"]}


# Construcción del grafo
builder = StateGraph(input=State, output=OutputState)

# Nodo a: Clasificar archivos
builder.add_node("brancher", ClassifyNode())
builder.add_edge(START, "brancher")

# Nodo b: Procesar imágenes
builder.add_node("extract from images", ImageNode())
builder.add_edge("brancher", "extract from images")

# Nodo c: Procesar archivos
builder.add_node("extract from pdf", PdfNode())
builder.add_edge("brancher", "extract from pdf")

# Nodo d: Fusionar resultados
builder.add_node("merger", merge_results)
builder.add_edge("extract from images", "merger")
builder.add_edge("extract from pdf", "merger")
builder.add_edge("merger", END)

extractor = builder.compile()



async def main():
    input_paths = [
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\- Factura 0003-00111312 -  - CARTOCOR S A .pdf",
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png"
    ]

    # Llama a la función `generate_json_from_pdfs` (debe ser adaptada para ser async si no lo es).
    data_json = generate_json_from_file(input_paths)
    
    # Llama a `extraction_node`, asegurándote de que también sea una función asincrónica.
    result = await extractor.ainvoke({"aggregate": [], "images": "", "files": "", "input_value": data_json})

    print("Salida: ", result)

# Ejecuta el evento principal asincrónico
if __name__ == "__main__":
    asyncio.run(main())
