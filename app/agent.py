import asyncio
from typing import TypedDict
from typing import Annotated, List, Sequence
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Define the schema for the input
class InputState(TypedDict):
    asunto: str
    cuerpo: str

# Define the schema for the output
class OutputState(TypedDict):
    categoria: str

# Define el estado del agente
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Función para devolver las categorías posibles
def get_categories() -> str:
    """Devuelve las categorías posibles de un correo electronico"""
    categories = [
        "Alta de usuario", "Diferencias en el pago", "Error de registración", "Estado de facturas",
        "Facturas no cobradas", "Facturas rechazadas", "Impresión de NC/ND", "Impresión de OP y/o Retenciones",
        "No figuran facturas", "Partidas bloqueadas Facturas", "Pedido devolución retenciones",
        "Presentación de facturas", "Problemas de acceso", "Salientes YPF"
    ]
    return "\n".join(categories)

#Funcion para devolver descripción de una categoría
# def get_categories(query:str) -> str:
#     """Devuelve las categorías posibles de un correo junto con sus descripciones"""
#     categories = {
#         "Alta de usuario": "Solicitudes relacionadas con la creación de un nuevo usuario en el sistema.",
#         "Diferencias en el pago": "Consultas sobre discrepancias en los montos o detalles de un pago realizado. Suele haber una clara mencion de las diferencias en el pago.",
#         "Error de registración": "Problemas al intentar registrar información en el sistema.",
#         "Estado de facturas": "Peticiones sobre el estado actual de facturas presentadas o procesadas.",
#         "Facturas no cobradas": "Consultas acerca de facturas que aún no han sido pagadas.",
#         "Facturas rechazadas": "Casos en los que las facturas han sido rechazadas por algún motivo.",
#         "Impresión de NC/ND": "Solicitudes relacionadas con la impresión de notas de crédito o débito.",
#         "Impresión de OP y/o Retenciones": "Pedidos para imprimir órdenes de pago o certificados de retenciones.",
#         "No figuran facturas": "Problemas relacionados con facturas que no aparecen en el sistema.",
#         "Partidas bloqueadas Facturas": "Situaciones en las que partidas relacionadas con facturas están bloqueadas.",
#         "Pedido devolución retenciones": "Consultas para solicitar la devolución de retenciones aplicadas.",
#         "Presentación de facturas": "Dudas o problemas sobre cómo presentar facturas para su procesamiento.",
#         "Problemas de acceso": "Inconvenientes para acceder al sistema o a una plataforma.",
#         "Salientes YPF": "Casos específicos relacionados con comunicaciones o gestiones externas de YPF.",
#         "Otras consultas": "Consultas generales que no encajan en ninguna de las categorías anteriores o de la que no se tiene suficiente informacion para resolver con certeza."
#     }
#     return "\n".join(categories)

# Crear la herramienta que devuelve las categorías
tools = [get_categories]

# Instruccion del agente de limpieza
cleaner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Eres un agente limpiador de emails. 
            Tu tarea consiste en limpiar cadenas de mails y obtener limpia la conversasion entre las personas intervinientes."
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Instruccion del agente
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Sos un categorizador de casos que se reciben por mail de un contact center de un equipo de facturación. 
            Vas a recibir un asunto y un cuerpo de un mail y tenés que categorizarlo.
            La respuesta solo puede ser alguna de las opciones posibles para categorizar un mail.
            Siempre brindas una pequeña explicación del porque escogiste la categoría en cuestión.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Define el modelo de OpenAI (reemplaza con tu configuración correcta)
llm = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",  
    api_version="2024-02-15-preview",
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)
llm_with_tools = llm.bind_tools(tools)

reflection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Eres un asistente experto en análisis de texto y validación de clasificaciones. 
            Tu tarea es analizar un texto junto con su categoría asignada y determinar si esa categoría tiene sentido o no. 
            Si la categoría no es adecuada, deberás explicar por qué al modelo que categoriza 
            para que pueda encontrar una mejor categoría.
            Tenés que tener en cuenta que los mensajes pueden venir ambiguos o con información faltante, en esos casos debe ser 'Otras consultas'""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

clean = cleaner_prompt | llm
generate = prompt | llm
reflect = reflection_prompt | llm

# Defino nodes
def input_node(state: InputState) -> State:
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
                    ["Alta de usuario", "Diferencias en el pago", "Error de registración", "Estado de facturas",
                    "Facturas no cobradas", "Facturas rechazadas", "Impresión de NC/ND", "Impresión de OP y/o Retenciones",
                    "No figuran facturas", "Partidas bloqueadas Facturas", "Pedido devolución retenciones",
                    "Presentación de facturas", "Problemas de acceso", "Salientes YPF"]
                    Si te parece que no aplica ninguna o la información parece incompleta entonces categorizalo como 'Otras consultas'."""
                )
            ]}

async def generation_node(state: State) -> State:
    result = await generate.ainvoke(state["messages"])
    return {"messages": [result]}


async def reflection_node(state: State) -> State:
    # Other messages we need to adjust
    # cls_map = {"ai": HumanMessage, "human": AIMessage}
    # # First message is the original user request. We hold it the same for all nodes
    # translated = [state["messages"][0]] + [
    #     cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    # ]
    # res = await reflect.ainvoke(translated)
    # # We treat the output of this as human feedback for the generator
    # return {"messages": [HumanMessage(content=res.content)]}

    # Obtener la última respuesta generada y la categoría asignada
    last_message = state["messages"][-1]  # La última respuesta generada

    # Reflexionar en base a la última respuesta y la categoría
    translated = [last_message, 
                  HumanMessage(
                    content="""¿Es la categoria asignada coherente con el contexto del mensaje? 
                    Si es que SI aclara en la respuesta 'GO TO END: "Categoría asignada"' donde categoría asignada es la categoría que se genero como respuesta.
                    Si es que NO el texto 'GO TO END' NO debe aparecer en el mensaje de salida.
                    Las categorias posibles son:\n
                    ["Alta de usuario", "Diferencias en el pago", "Error de registración", "Estado de facturas",
                    "Facturas no cobradas", "Facturas rechazadas", "Impresión de NC/ND", "Impresión de OP y/o Retenciones",
                    "No figuran facturas", "Partidas bloqueadas Facturas", "Pedido devolución retenciones",
                    "Presentación de facturas", "Problemas de acceso", "Salientes YPF", "Otras consultas"]."""
                )]
    res = await reflect.ainvoke(translated)

    # Devolver el estado con la nueva reflexión
    return {"messages": [HumanMessage(content=res.content)]}

def output_node(state: State) -> OutputState:
    last_message = state["messages"][-1].content  # Obtener el último mensaje
    if "GO TO END:" in last_message:
        categoria = last_message.split("GO TO END:")[-1].strip()  # Extraer el valor después de "GO TO END:"
        return OutputState(categoria=categoria)
    return OutputState(categoria="Desconocida")  # Valor por defecto si no se encuentra el texto


builder = StateGraph(State, input=InputState, output=OutputState)
builder.add_node("input", input_node)
builder.add_node("generate", generation_node)
builder.add_node("tools", ToolNode(tools))
builder.add_node("reflect", reflection_node)
builder.add_node("output", output_node)

# Defino edges
def should_continue(state: State):
    last_message = state["messages"][-1].content if state["messages"] else ""
    if "GO TO END" in last_message:
        return True
    if len(state["messages"]) > 10:
        return True
    return False


builder.add_edge(START, "input")
builder.add_edge("input", "generate")
builder.add_conditional_edges("generate",tools_condition)
builder.add_edge("tools", "generate")
builder.add_edge("generate", "reflect")
builder.add_conditional_edges("reflect", should_continue, {True: "output", False: "generate"})
builder.add_edge("output", END)
memory = MemorySaver()

# Defino graph
graph = builder.compile(checkpointer=memory)
config = {"configurable": {"thread_id": "1"}}

async def run_graph():
    
    async for event in graph.astream(
        {
            "messages": State['messages'],
        },
        config,
    ):
        print(event)
        print("---")

# Función principal para ejecutar todo el flujo
async def main():
    await run_graph()
    state = graph.get_state(config)
    ChatPromptTemplate.from_messages(state["messages"]).pretty_print()

# Iniciar el ciclo de eventos
if __name__ == "__main__":
    asyncio.run(main())


