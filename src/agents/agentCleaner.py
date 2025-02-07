from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from src.configs.Prompt_Template import cleaner_definition
from src.configs.llms import llm4o
from src.configs.classes import Input

class Cuerpo(TypedDict):
    cuerpo:Annotated[str, ...]

clean = cleaner_definition | llm4o.with_structured_output(Cuerpo)

# Defino nodes
def clean_body(state: Input) -> Input:
    cuerpo_filtrado = clean.invoke([HumanMessage(
        content = f"""Limpia el siguiente mail:\n{state["cuerpo"]}""")])
    return {"cuerpo":cuerpo_filtrado}

def clean_attachments(state: Input) -> Input:
    if len(state["adjuntos"]) == 0:
        return state
    
    return state

builder = StateGraph(input=Input, output=Input)

builder.add_node("Clean body", clean_body)
builder.add_node("Clean attachments", clean_attachments)

builder.add_edge(START, "Clean body")
builder.add_edge("Clean body", "Clean attachments")
builder.add_edge("Clean attachments", END)

cleaner = builder.compile()
