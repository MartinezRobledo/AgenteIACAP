import operator
from typing import Annotated, Any
from src.utils.armar_json_adjuntos_b64 import generate_json_from_file
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    # La lista `aggregate` acumulará valores
    aggregate: Annotated[list, operator.add]
    value_for_b: list  # Almacena el valor para "b"
    value_for_c: list  # Almacena el valor para "c"
    input_value: list  # Valor recibido desde START


class NodeA:
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
        value_for_b = images
        value_for_c = others
        return {"value_for_b": value_for_b, "value_for_c": value_for_c}


class NodeB:
    def __call__(self, state: State) -> Any:
        # "b" retorna lo que recibió de "a"
        value_from_a = state["value_for_b"]
        return {"aggregate": [value_from_a]}


class NodeC:
    def __call__(self, state: State) -> Any:
        # "c" retorna lo que recibió de "a"
        value_from_a = state["value_for_c"]
        return {"aggregate": [value_from_a]}


class NodeD:
    def __call__(self, state: State) -> Any:
        # "d" simplemente combina lo que está en `aggregate`
        return {"aggregate": state["aggregate"]}


# Construcción del grafo
builder = StateGraph(State)

# Nodo "a" clasifica y envía valores a "b" y "c"
builder.add_node("a", NodeA())
builder.add_edge(START, "a")

# Nodo "b" recibe y retorna su valor
builder.add_node("b", NodeB())
builder.add_edge("a", "b")

# Nodo "c" recibe y retorna su valor
builder.add_node("c", NodeC())
builder.add_edge("a", "c")

# Nodo "d" combina resultados de "b" y "c"
builder.add_node("d", NodeD())
builder.add_edge("b", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)

# Compilar el grafo
graph = builder.compile()

input_paths = [
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\- Factura 0003-00111312 -  - CARTOCOR S A .pdf",
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png"
    ]

# Llama a la función `generate_json_from_pdfs` (debe ser adaptada para ser async si no lo es).
data_json = generate_json_from_file(input_paths)

# Ejecutar el grafo con un estado inicial vacío
result = graph.invoke({"aggregate": [], "value_for_b": "", "value_for_c": "", "input_value": data_json})

print(f"Final result: {result['aggregate']}")
