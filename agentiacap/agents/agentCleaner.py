from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from agentiacap.llms.Prompts import cleaner_definition
from agentiacap.llms.llms import llm4o
from agentiacap.utils.globals import InputSchema

class Cuerpo(TypedDict):
    cuerpo:Annotated[str, ...]

clean = cleaner_definition | llm4o.with_structured_output(Cuerpo)

# Defino nodes
def clean_body(state: InputSchema) -> InputSchema:
    try:
        cuerpo_filtrado = clean.invoke([HumanMessage(
            content=f"""Limpia el siguiente mail:\n{state['cuerpo']}""")])
        return {"cuerpo": cuerpo_filtrado}
    except Exception as e:
        raise RuntimeError(f"Error al limpiar el cuerpo del mail: {e}")

def clean_attachments(state: InputSchema) -> InputSchema:
    try:
        if len(state["adjuntos"]) == 0:
            return state
        # Lógica adicional para limpiar o procesar los adjuntos si es necesario
        return state
    except Exception as e:
        raise RuntimeError(f"Error al procesar los adjuntos: {e}")


builder = StateGraph(input=InputSchema, output=InputSchema)

builder.add_node("Clean body", clean_body)
builder.add_node("Clean attachments", clean_attachments)

builder.add_edge(START, "Clean body")
builder.add_edge("Clean body", "Clean attachments")
builder.add_edge("Clean attachments", END)

cleaner = builder.compile()
