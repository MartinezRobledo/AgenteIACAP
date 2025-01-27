from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain_openai import AzureChatOpenAI
import random
import json

json_file = "D:\\Python\\agents\\app\\SkLearn\\Ejemplos.json"

# Functions
def obtener_casos(categoria, n=5):
    """
    Obtiene un número definido de casos aleatorios de una categoría específica.
    
    Args:
        categoria (str): La categoría a buscar.
        n (int): Número de casos a devolver.

    Returns:
        list: Lista con hasta `n` textos de la categoría solicitada.
    """
    # Cargar el archivo JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrar casos que pertenecen a la categoría solicitada
    casos_filtrados = [item["Datos"] for item in data if item["Categoria"] == categoria]
    
    # Verificar si hay suficientes casos
    if not casos_filtrados:
        raise ValueError(f"No se encontraron casos para la categoría '{categoria}'.")

    # Seleccionar aleatoriamente hasta `n` casos
    return random.sample(casos_filtrados, min(len(casos_filtrados), n))

def armar_prompt(categoria, casos, email):
    """
    Construye un prompt para el modelo de lenguaje.

    Args:
        categoria (str): Categoría del análisis.
        casos (list): Lista de textos de ejemplo.
        texto_entrada (str): Texto que se evaluará.

    Returns:
        str: Prompt para el modelo de lenguaje.
    """
    prompt = f"""Eres un modelo de IA que compara textos de emails para evaluar si comparten el mismo contexto. 
    La categoría que estamos analizando es '{categoria}'. A continuación, te proporciono algunos casos de ejemplo para esta categoría:

    {chr(10).join(f"- {caso}" for caso in casos)}

    Ahora, evalúa si el siguiente email que estamos procesando pertenece a esta categoría basándote en los ejemplos:
    Email entrada: {email}

    Responde con un nivel de similitud del 0 al 100 sobre si el email pertenece al mismo contexto que los casos proporcionados.
    """
    return prompt

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

def evaluar_contexto(categoria: str, email_entrada: str) -> str:
    """
    Evalúa si un email pertenece a una categoría en base a ejemplos y devuelve el nivel de certeza.

    Args:
        categoria (str): Categoría del análisis.
        email_entrada (str): Email que se evaluará.

    Returns:
        str: Nivel de certeza proporcionado por el modelo.
    """
    try:
        # Obtener 5 casos aleatorios de la categoría
        casos = obtener_casos(categoria, n=5)
        
        # Armar el prompt
        prompt = armar_prompt(categoria, casos, email_entrada)
        
        # Llamar al modelo de Azure OpenAI
        respuesta = llm.invoke([HumanMessage(content=prompt)])
        
        # Procesar la respuesta del modelo
        nivel_certeza = respuesta.content.strip()
        print("NIVEL CERTEZA: ", nivel_certeza)
        return nivel_certeza
    except Exception as e:
        print("ERROR en TOOL: ", e)
        return f"Error: {str(e)}"

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",  
    api_version="2024-02-15-preview",
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)
llm_with_tools = llm.bind_tools([multiply, evaluar_contexto])

# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_node("tools", ToolNode([multiply, evaluar_contexto]))
builder.add_edge(START, "tool_calling_llm")
builder.add_conditional_edges(
    "tool_calling_llm",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", END)
graph = builder.compile()

# View
display(Image(graph.get_graph().draw_mermaid_png()))

from langchain_core.messages import HumanMessage
messages = [HumanMessage(content="""
    ¿Es la categoría asignada coherente con el contexto del email? Para validar esto utilizá la tool 'evaluar contexto'.
    #         Si es que SI aclara en la respuesta 'APROBADA: "Categoría asignada"' donde categoría asignada es la categoría que se generó como respuesta.
    #         Si es que NO aclara en la respuesta 'RECHAZADA'.
    Categoría asignada: Problemas de acceso
    Email: "Estimados,

Estamos imposibilitados de acceder a la extranet de proveedores. La web
constantemente indica “contraseña incorrecta”. Evidentemente la misma no
funciona.

 

Les pido por favor el detalle de los pagos realizados a nuestra firma
(incluyendo retenciones) los días 8/1/25 y 15/1/25.

 

GALZZI SRL

CUIT 30708460687

 

Gracias

 

Saludos,

 

Ing. Matías Balduzzi

Desarrollo Comercial

[cid:image001.png@01DB679E.5487C800]

Av. Juan B. Alberdi 965 - 9 ""21"" - CABA

Tel.: 011 15-6487-2006 / 011 15 4490-4314

 "

""")]
messages = graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()