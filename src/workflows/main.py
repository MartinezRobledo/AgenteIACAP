from langgraph.graph import StateGraph, START, END, MessagesState
from src.agents.agentCleaner import cleaner
from src.agents.agentClassifier import classifier
from src.agents.agentExtractor import extractor
from src.configs.classes import Mail, Input, Output


# Recibimos Asunto, Cuerpo, Adjunto.
# Se debe limpiar el cuerpo del mensaje
# Se debe determinar si los adjuntos no son redundantes
# 1. Clasificar Mail por asunto y cuerpo
# 2. Contemplar existencia de adjuntos para mejorar la clasificación
# 3. Obtener información de adjuntos en base a la clasificación
# 4. Retornar categoría del mail y datos del adjunto según corresponda.

# Instanciamos el mail a procesar
mail:Mail

# Nodo de entrada de datos
def input_node(input:Input) -> Input:
    mail = input
    

# Nodo de salida de datos
def output_node(data:dict) -> Output:
    return Output(data=data, categoría=mail._categoría)

# Workflow principal
builder = StateGraph(MessagesState, input=Input, output=Output)
builder.add_node("Input", input_node)
builder.add_node("Cleaner", cleaner)
builder.add_node("Classifier", classifier)
builder.add_node("Extractor", extractor)
builder.add_node("Output", output_node)

builder.add_edge(START, "Input")
builder.add_edge("Input", "Cleaner")
builder.add_edge("Cleaner", "Classifier")
builder.add_edge("Classifier", "Extractor")
builder.add_edge("Extractor", "Output")
builder.add_edge("Output", END)

graph = builder.compile()