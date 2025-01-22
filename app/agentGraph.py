from typing import TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END, MessagesState

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
            """Eres un agente limpiador de emails. 
            Tu tarea consiste en limpiar cadenas de mails y obtener limpia la conversación entre las personas intervinientes.
            No das explicaciones de los pasos que realizaste solo brindas el mail formateado y limpio."
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
            Para esto vas a hacer uso de las categorías y descripciones que se te brinden. 
            Si la categoría no es adecuada, deberás explicar por qué al modelo que categoriza para que pueda encontrar una mejor categoría.
            Tienes que tener en cuenta que los mensajes pueden venir ambiguos o con información faltante, y tambien pueden no encajar en ninguna categoría, en esos casos debe ser 'Otras consultas'.""",
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
classiffier = prompt | llm4o
reflect = reflection_prompt | llm4o

# Defino nodes
def input_node(state: InputState) -> MessagesState:
    cuerpo_filtrado = clean.invoke([HumanMessage(
        content = f"""Limpia el siguiente cuerpo de mail:\n
            {state['cuerpo']}
        """
    )])
    # print("Consumo total de tokens cleaner: ", cuerpo_filtrado.response_metadata['token_usage']['total_tokens'])
    return {"messages": [
                HumanMessage(
                    content=f"""A continuación te dejo el siguiente mail para que lo categorices,\n
                    Asunto: {state['asunto']}.\n
                    Cuerpo: {cuerpo_filtrado}.\n
                    Las categorias posibles son:\n
                    {categories}
                    Si te parece que no aplica ninguna o la información parece incompleta entonces categorizalo como 'Otras consultas'."""
                )
            ]}

async def classifier_node(state: MessagesState) -> MessagesState:
    result = await classiffier.ainvoke(state["messages"])
    # print("Consumo total de tokens classifier: ", result.response_metadata['token_usage']['total_tokens'])
    return {"messages": [result]}


async def reflection_node(state: MessagesState) -> MessagesState:
    # Other messages we need to adjust
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    # First message is the original user request. We hold it the same for all nodes
    translated = [state["messages"][0]] + [
        cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    ]
    translated.append(
        HumanMessage(
            content=f"""¿Es la categoria asignada coherente con el contexto del mensaje? 
            Si es que SI aclara en la respuesta 'GO TO END: "Categoría asignada"' donde categoría asignada es la categoría que se genero como respuesta.
            Si es que NO el texto 'GO TO END' NO debe aparecer en el mensaje de salida.
            Las categorias posibles son:\n
            {categories}
            """
    ))
    res = await reflect.ainvoke(translated)
    # print("Consumo total de tokens reflect: ", res.response_metadata['token_usage']['total_tokens'])
    # We treat the output of this as human feedback for the generator
    return {"messages": [HumanMessage(content=res.content)]}

def output_node(state: MessagesState) -> OutputState:
    last_message = state["messages"][-1].content  # Obtener el último mensaje
    if "GO TO END:" in last_message:
        categoria = last_message.split("GO TO END:")[-1].strip()  # Extraer el valor después de "GO TO END:"
        return OutputState(categoria=categoria)
    return OutputState(categoria="Desconocida")  # Valor por defecto si no se encuentra el texto, Desconocida = Excepcion.


builder = StateGraph(input=InputState, output=OutputState)
builder.add_node("input", input_node)
builder.add_node("classifier", classifier_node)
builder.add_node("reflect", reflection_node)
builder.add_node("output", output_node)

# Defino edges
def should_continue(state: MessagesState):
    last_message = state["messages"][-1].content if state["messages"] else ""
    if "GO TO END" in last_message:
        return True
    if len(state["messages"]) > 10:
        return True
    return False


builder.add_edge(START, "input")
builder.add_edge("input", "classifier")
builder.add_edge("classifier", "reflect")
builder.add_conditional_edges("reflect", should_continue, {True: "output", False: "classifier"})
builder.add_edge("output", END)

# Defino graph
graph = builder.compile()
