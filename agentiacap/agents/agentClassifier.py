import re
from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from agentiacap.llms.llms import llm4o
from agentiacap.utils.globals import InputSchema
from agentiacap.llms.Prompts import categories, reflection_definition, classifier_definition
from agentiacap.tools.evaluate_context import evaluar_contexto

categories = "\n".join(categories)

classification = classifier_definition | llm4o
llm_with_tools = reflection_definition | llm4o.bind_tools([evaluar_contexto])

class OutputState(TypedDict):
    categoria:Annotated[str, ...]

def input_node(state: InputSchema) -> MessagesState:
    try:
        return {
            "messages": [
                HumanMessage(
                    content=f"""A continuación te dejo el siguiente mail para que lo categorices,\n
                    Asunto: {state['asunto']}.\n
                    Cuerpo: {state['cuerpo']}.\n
                    Las categorias posibles son:\n
                    {categories}
                    Si te parece que no aplica ninguna o la información parece escasa, incompleta o ambigua entonces categorizalo como 'Otras consultas'."""
                )
            ]
        }
    except Exception as e:
        raise ValueError(f"Error al generar el nodo de entrada: {e}")

async def classifier_node(state: MessagesState) -> MessagesState:
    try:
        result = await classification.ainvoke(state["messages"])
        return {"messages": [HumanMessage(content=result.content)]}
    except Exception as e:
        raise RuntimeError(f"Error al invocar el clasificador: {e}")

async def reflection_node(state: MessagesState) -> MessagesState:
    try:
        prompt = HumanMessage(
                content="""¿Es la categoría asignada coherente con el contexto del email? Para validar esto utilizá la tool 'evaluar contexto'."""
            )
        response = llm_with_tools.invoke(state["messages"] + [prompt])
        return {"messages": state["messages"] + [response]}
    except Exception as e:
        raise RuntimeError(f"Error al invocar la reflexión: {e}")

def output_node(state: MessagesState) -> OutputState:
    try:
        match = re.search(r"APROBADA:\s*\"([^\"]+)\"", state["messages"][-1].content)
        if match:
            categoria = match.group(1)  # Extraer el valor después de "APROBADA:"
            return {"categoria": categoria}
        return {"categoria": "Otras consultas"}  # Valor por defecto si no se logró aprobar la categoría.
    except Exception as e:
        raise RuntimeError(f"Error al generar la salida: {e}")

# Defino edges
def should_continue(state: MessagesState) -> str:
    try:
        if "APROBADA" in state["messages"][-1].content:
            return "output"  # Si está aprobada, avanza al nodo output
        else:
            return "classifier"  # Si está rechazada, regresa al clasificador
    except Exception as e:
        raise RuntimeError(f"Error al evaluar si continuar: {e}")

# Defino grafo
builder = StateGraph(MessagesState, input=InputSchema, output=OutputState)

builder.add_node("input", input_node)
builder.add_node("classifier", classifier_node)
builder.add_node("reflect", reflection_node)
builder.add_node("tools", ToolNode([evaluar_contexto]))
builder.add_node("output", output_node)

builder.add_edge(START, "input")
builder.add_edge("input", "classifier")
builder.add_edge("classifier", "reflect")
builder.add_conditional_edges("reflect", tools_condition, {"tools":"tools", END:"output"})
builder.add_conditional_edges("tools", should_continue, ["output", "classifier"])
builder.add_edge("output", END)

# Instancio graph
classifier = builder.compile()