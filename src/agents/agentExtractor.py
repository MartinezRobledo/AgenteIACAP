import asyncio
import random
import json
import re
from typing import TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

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
    Estima el nivel de similitud en un rango del 0 al 100 y contempla un umbral de 80 para aprobar o rechazar la categoría.
    Si supera el umbral aclara en la respuesta 'APROBADA: "Categoría asignada"' donde categoría asignada es la categoría que se generó como respuesta.
    Si es que NO supera el umbral aclara en la respuesta 'RECHAZADA'.
    """
    return prompt

# Define the schema for the input
class InputState(TypedDict):
    asunto: str
    cuerpo: str

# Define the schema for the output
class OutputState(TypedDict):
    categoria: str

categories = [
    "Categoría: Alta de usuario, Descripción: Se suele pedir explícitamente en el asunto o en el cuerpo del mail. Sujeto a palabras claves dentro del contexto de la generación o gestión de un nuevo usuario.",
    "Categoría: Error de registración, Descripción: el reclamo siempre es por fechas de vencimiento mal aplicadas. Sujeto al contexto en que el proveedor reclama una mala asignación de la fecha de vencimiento de su factura en el sistema.", 
    "Categoría: Estado de facturas, Descripción: Consultas sobre estado de facturas, facturas pendientes, facturas vencidas, facturas impagas, facturas no cobradas.",
    "Categoría: Facturas rechazadas, Descripción: Se suele aclarar explícitamente en el asunto o en el cuerpo del mail que la factura fue rechazada. Sujeto a contexto en que se pide motivo del rechazo de una factura.", 
    "Categoría: Impresión de NC/ND, Descripción: Ahora se llama “Multas”. Sujeto a palabras clave relacionadas con Multas. Sujeto al contexto en que se reclama o consulta por diferencias en el pago . ", 
    "Categoría: Impresión de OP y/o Retenciones, Descripción: Suele ser una solicitud o pedido de ordenes de pago (OP) o retenciones. Suele estar explicito en el asunto o en el cuerpo del mail un mensaje pidiendo retenciones/OP.",
    "Categoría: Pedido devolución retenciones, Descripción: Suele estar explicito en el asunto o cuerpo del mail. Sujeto a palabras clave relacionadas con una devolución o reintegro de una retención. También se suele hacer mención con frecuencia que se envía una nota o se adjunta una nota solicitando a la devolución del monto retenido.",
    "Categoría: Presentación de facturas, Descripción: Sujeto al contexto en que el proveedor adjunta una factura y aclara el numero de la factura. Puede explicitar que es una presentación en el asunto como puede no hacerlo, pero siempre se va a referir a un mensaje que indica el adjunto de una factura. Esta no es una categoría en la que entren consultas.", 
    "Categoría: Problemas de acceso, Descripción: Sujeto al contexto en que se reclama por no poder acceder a facturar u obtener información de una factura. No se solicita información de una factura solo se reclama el acceso al sistema.", 
    "Categoría: Salientes YPF, Descripción: No se aclara explícitamente el texto “Salientes YPF”. Está sujeto al contexto en que se pide INFORMAR AL PROVEEDOR de algo."
    "Categoría: Otras consultas, Descripción: Consultas generales que no encajan en ninguna de las categorías."
]
categories = "\n".join(categories)

# Instruccion del agente de limpieza
cleaner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Eres un agente especializado en limpiar correos electrónicos. Tu tarea es extraer únicamente la conversación relevante entre las partes involucradas (como preguntas, respuestas y comentarios útiles). Debes eliminar todo lo que no sea parte de la conversación directa, incluyendo:

            Firmas automáticas (nombre, cargo, empresa, teléfonos, etc.).
            Cabeceras de correo (como "De:", "Para:", "Asunto:", "Enviado:").
            Respuestas previas repetidas en cadenas largas de correos.
            Publicidad, disclaimers legales, y pie de página.
            Texto decorativo o irrelevante (como saludos genéricos y despedidas excesivamente largas).
            Reglas para procesar el email:

            Conserva solo el intercambio de mensajes relevante entre las partes.
            Mantén el texto legible y organizado en un formato limpio.
            No alteres el contenido relevante ni lo parafrasees.
            Ignora elementos irrelevantes como saludos triviales o cortesías sin importancia.
            Devuelve el resultado como un bloque de texto claro y organizado.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Instruccion del agente clasificador
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Sos un categorizador de casos que se reciben por mail de un contact center de un equipo de facturación. 
            Vas a recibir un asunto y un cuerpo de un mail y tenés que categorizarlo en base a las categorías que te indiquen.
            La respuesta solo puede ser alguna de las opciones posibles para categorizar un mail y te vas a basar en la descripción de la categoría para hacerlo.
            La respuesta que des tiene que incluir el mail que recibiste para analizar y la categoría que terminaste eligiendo.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Instruccion del agente que reflexiona
reflection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Eres un asistente experto en análisis de texto y validación de clasificaciones. 
            Tu tarea es validar si el mail que se te brinda junto con su categoría asignada es coherente con su descripción.
            Para esto vas a hacer uso de una tool que te va a devolver un nivel de certeza entre 0 y 100 basado en ejemplos de la misma categoría. 
            Si la categoría no es mayor a un 80 porciento de similitud, deberás rechazar la categoría e indicarle al clasificador que no hay similitud con los ejemplos.
            Si la categoría es 'Otras consultas' aprobala directamente SIN buscar ejemplos.""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Define el modelo de OpenAI (reemplaza con tu configuración correcta)
llm4o = AzureChatOpenAI(
    azure_deployment="gpt-4o",  
    api_version="2024-02-15-preview",
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)

llm4o_mini = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",  
    api_version="2024-02-15-preview",
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)


clean = cleaner_prompt | llm4o_mini
classifier = prompt | llm4o
reflect = reflection_prompt | llm4o

# Tools
def evaluar_contexto(categoria: str, email_entrada: str) -> MessagesState:
    """
    Evalúa si un email pertenece a una categoría en base a ejemplos precargados en la tool y devuelve un booleano para indicar la validación.

    Args:
        categoria (str): Categoría a evaluar.
        email_entrada (str): Email que se evaluará.

    Returns:
        bool: Es valido.
    """
    # Obtener 5 casos aleatorios de la categoría
    casos = obtener_casos(categoria, n=5)
    
    # Armar el prompt
    prompt = armar_prompt(categoria, casos, email_entrada)
    
    # Llamar al modelo de Azure OpenAI
    respuesta = llm4o.invoke([HumanMessage(content=prompt)])
    
    return {"messages": [respuesta]}


llm_with_tools = llm4o.bind_tools([evaluar_contexto])


# Defino nodes
def input_node(state: InputState) -> MessagesState:
    cuerpo_filtrado = clean.invoke([HumanMessage(
        content = f"""Limpia el siguiente cuerpo de mail:\n
            {state['cuerpo']}
        """
    )])
    return {"messages": [
                HumanMessage(
                    content=f"""A continuación te dejo el siguiente mail para que lo categorices,\n
                    Asunto: {state['asunto']}.\n
                    Cuerpo: {cuerpo_filtrado}.\n
                    Las categorias posibles son:\n
                    {categories}
                    Si te parece que no aplica ninguna o la información parece escasa, incompleta o ambigua entonces categorizalo como 'Otras consultas'."""
                )
            ]}

async def classifier_node(state: MessagesState) -> MessagesState:
    result = await classifier.ainvoke(state["messages"])
    return {"messages": state["messages"] + [HumanMessage(content=result.content)]}

async def reflection_node(state: MessagesState) -> MessagesState:
    prompt = HumanMessage(
            content="""¿Es la categoría asignada coherente con el contexto del email? Para validar esto utilizá la tool 'evaluar contexto'.
            """
        )
    response = llm_with_tools.invoke(state["messages"]+[prompt])
    return {"messages": state["messages"]+[response]}


def output_node(state: MessagesState) -> OutputState:
    match = re.search(r"APROBADA:\s*\"([^\"]+)\"", state["messages"][-1].content)
    if match:
        categoria = match.group(1)  # Extraer el valor después de "APROBADA:"
        return OutputState(categoria=categoria)
    return OutputState(categoria="Otras consultas")  # Valor por defecto si no se logró aprobar la categoría.

builder = StateGraph(MessagesState, input=InputState, output=OutputState)
builder.add_node("input", input_node)
builder.add_node("classifier", classifier_node)
builder.add_node("reflect", reflection_node)
builder.add_node("tools", ToolNode([evaluar_contexto]))
builder.add_node("output", output_node)

# Defino edges
def should_continue(state: MessagesState) -> str:
    if "APROBADA" in state["messages"][-1].content:
        return "output"  # Si está aprobada, avanza al nodo output
    else:
        return "classifier"  # Si está rechazada, regresa al clasificador

builder.add_edge(START, "input")
builder.add_edge("input", "classifier")
builder.add_edge("classifier", "reflect")
builder.add_conditional_edges("reflect", tools_condition, {"tools":"tools", END:"output"})
builder.add_conditional_edges("tools", should_continue, ["output", "classifier"])
builder.add_edge("output", END)

# Defino graph
extractor = builder.compile()


async def run():
    input_state = InputState(asunto="Consulta acceso Del Plata Ingenieria Austral", cuerpo=""""> Buen día, espero que se encuentren bien!
> 
> 
> 
> Les escribo de Del Plata Ingeniería,
> 
> 
> 
> Nosotros podemos acceder sin problemas al portal para consultar pagos de Del
> Plata Ingeniería S.A.:
> 
> usuario: jolivares@dpisa.com.ar
> 
> contraseña: Tigresa7
> 
> 
> 
> Pero en Del Plata Ingenieria Autral S.A. (CUIT 30710984006) no podemos
> ingresar ya que no tenemos acceso al mail con el que estábamos registrados
> porque esta persona no pertenece más a la empresa: lfernandez@dpisa.com.ar
> 
> 
> 
> Queria saber como podemos ingresar para consultar los pagos de Del Plata
> Ingenieria Austral, si podemos gestionar un nuevo usuario o agregar al
> usuario jolivares@dpisa.com.ar el acceso también a la otra cuenta.
> 
> 
> 
> Muchas gracias!
> 
> 
> 
> 
> [cid:0.28873824440.754332274613737423.1946ab5c2a5__inline__img__src]
> 
> Juan Ignacio Bonifazi
> Analista de Facturación y Cobranzas
> Cel:
> www.dpisa.com.ar [http://www.dpisa.com.ar/]
> 
> 
> [cid:1.28873824440.1340335054609618804.1946ab5c2a5__inline__img__src]



"
""")
    messages = await graph.ainvoke(input_state)
    print("Salida: ", messages['categoria'])

asyncio.run(run())