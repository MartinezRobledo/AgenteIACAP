import asyncio
import operator
from src.services.tools.document_intelligence import process_base64_files, process_base64_images
from src.utils.armar_json_adjuntos_b64 import generate_json_from_file
from typing import Annotated, Any, List, Dict
from langgraph.graph import StateGraph, START, END

class State:
    results: Annotated[list, operator.add]

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

def classify_files(state: State, files: List[Dict]) -> Dict:
    """
    Clasifica los archivos en imágenes y otros tipos.
    """
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
    images, others = [], []

    for file in files:
        file_name = file.get("file_name", "").lower()
        if file_name.endswith(image_extensions):
            images.append(file)
        else:
            others.append(file)

    print("Clasificación completada.")
    return {"images": images, "others": others}

def input_node(attachments:list) -> list:
    categorized_files = classify_files(attachments)


async def extraction_file_node(files:list) -> dict:
    return process_base64_files(base64_files=files, fields_to_extract=fields_to_extract)

async def extraction_image_node(images:list) ->dict:
    return process_base64_images(base64_images=images, fields_to_extract=fields_to_extract)


def merge_results(state: State, images_result: List[Dict], files_result: List[Dict]) -> List[Dict]:
    """
    Combina los resultados de imágenes y archivos.
    """
    print("Fusionando resultados...")
    return images_result + files_result

# Construcción del grafo
builder = StateGraph(State)

# Nodo a: Clasificar archivos
builder.add_node("brancher", lambda state, files: classify_files(state, files))
builder.add_edge(START, "input")

# Nodo b: Procesar imágenes
builder.add_node("extract to images", lambda state, images: extraction_image_node(state, images))
builder.add_edge("brancher", "extract to images", condition=lambda outputs: outputs["images"])

# Nodo c: Procesar archivos
builder.add_node("extract to files", lambda state, files: extraction_file_node(state, files))
builder.add_edge("brancher", "extract to files", condition=lambda outputs: outputs["others"])

# Nodo d: Fusionar resultados
builder.add_node("merger", lambda state, images_result, files_result: merge_results(state, images_result, files_result))
builder.add_edge("extract to images", "merger")
builder.add_edge("extract to files", "merger")
builder.add_edge("merger", END)

async def main():
    input_paths = [
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\- Factura 0003-00111312 -  - CARTOCOR S A .pdf",
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png"
    ]

    # Llama a la función `generate_json_from_pdfs` (debe ser adaptada para ser async si no lo es).
    file_json = generate_json_from_file(input_paths)
    
    # Llama a `extraction_node`, asegurándote de que también sea una función asincrónica.
    data = await extraction_file_node(file_json)

    print(f"Extracción exitosa:\n{data}")

# Ejecuta el evento principal asincrónico
if __name__ == "__main__":
    asyncio.run(main())
