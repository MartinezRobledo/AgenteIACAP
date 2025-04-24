import json
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage
from agentiacap.tools.busqueda_sap import SAP_buscar_por_factura, SAP_buscar_por_fecha_monto, SAP_buscar_por_fecha_base
from agentiacap.llms.llms import llm4o
from agentiacap.utils.descargar_blob import obtener_blob_azure
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage
from langchain_core.messages import ToolMessage

class SAPAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], "El historial del chat"]
    inputs: Annotated[list, "Los datos a buscar"]
    files: Annotated[list, "Los blobs en Azure"]
    outputs: Annotated[list, "Las Ops encontradas"]

sys_msg = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente experto en búsqueda de datos. Contás con herramientas que te permiten realizar las búsquedas necesarias.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

tools = [SAP_buscar_por_factura, SAP_buscar_por_fecha_monto, SAP_buscar_por_fecha_base, obtener_blob_azure]

llm_with_tools = sys_msg | llm4o.bind_tools(tools)

def agent_node(state: SAPAgentState):
    prompt = HumanMessage(
                content=f"""
    Tenés el siguiente objeto de entrada:
    {state["inputs"]}
    y tenés el/los nombres de blobs cargados en Azure:
    {state["files"]}

    Decidí qué herramienta usar entre las siguientes:
    1. 'Buscar por factura': si tiene número de factura como '0001-00012345'
    2. 'Buscar por fecha y monto': si tiene ambos campos 'fecha' y 'monto'
    3. 'Buscar por fecha sola': si solo tiene 'fecha'
    4. 'Descargar blob de Azure': para ir obteniendo los archivos que se le deben pasar a las tools.

    Elegí la herramienta más adecuada, explicá por qué la elegiste, ejecutala y devolvé el siguiente JSON (en formato Python dict):

    {{
    "input": <elemento de la lista "inputs" que se procesó>,
    "tool": "<nombre de la herramienta usada>",
    "explicación": "<explicación lógica>",
    "output": <resultado de la función>
    }}
    Vas a ir agregandolo al campo outputs.
    Si no encontrás suficiente información para decidir, indicá que no se puede procesar y dejá output en None.
    """
    )
    
    # Llamada al LLM
    response = llm_with_tools.invoke(state["messages"] + [prompt])
    
    # Verificar si la respuesta tiene 'tool_calls' y asociarla correctamente
    if 'tool_calls' in response.additional_kwargs:
        # Extraer el tool_call de la respuesta
        tool_call = response.additional_kwargs['tool_calls'][0]
        tool_name = tool_call['function']['name']
        tool_args = tool_call['function']['arguments']
        
        # Verificar que tool_args sea un diccionario, si es un string lo deserializamos
        if isinstance(tool_args, str):
            tool_args = json.loads(tool_args)  # Convertir el string a un diccionario
            
        # Ejecución de herramientas
        if tool_name == 'obtener_blob_azure':
            # Llamada real a la función obtener_blob_azure
            result = obtener_blob_azure(**tool_args)
        
        elif tool_name == 'SAP_buscar_por_factura':
            # Llamada a la herramienta SAP_buscar_por_factura
            result = SAP_buscar_por_factura(**tool_args)
        
        elif tool_name == 'SAP_buscar_por_fecha_monto':
            # Llamada a la herramienta SAP_buscar_por_fecha_monto
            result = SAP_buscar_por_fecha_monto(**tool_args)
        
        elif tool_name == 'SAP_buscar_por_fecha_base':
            # Llamada a la herramienta SAP_buscar_por_fecha_base
            result = SAP_buscar_por_fecha_base(**tool_args)
        
        else:
            # Si la herramienta no está definida, manejarlo de alguna manera
            result = {"error": "Herramienta no reconocida"}
        
        # Crear el mensaje con el rol 'tool' y la salida de la herramienta
        tool_message = ToolMessage(
            tool_call_id=tool_call["id"],  # este ID viene del LLM que pidió la herramienta
            content=str(result)
        )
        state["messages"].append(tool_message)  # Añadir el mensaje con la respuesta de la herramienta
        
        # Asegurarse de que se devuelva el resultado con la estructura correcta
        return {"messages": state["messages"], "tool_output": result}
    
    # Si no se ha invocado ninguna herramienta, devolver solo los mensajes
    return {"messages": state["messages"]}



# Definir el grafo
builder = StateGraph(SAPAgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
    {"tools":"tools", END:END}
)
builder.add_edge("tools", "agent")
builder.add_edge("agent", END)

# Compilar el grafo
agente_sap = builder.compile()
