from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from src.configs.Prompt_Template import cleaner_definition
from src.configs.llms import llm4o_mini
from src.configs.classes import Input

clean = cleaner_definition | llm4o_mini

# Defino nodes
def clean_body(state: Input) -> Input:
    # if not isinstance(state, Input):
    #     raise TypeError("El estado debe ser una instancia de la clase Input.")
    cuerpo_filtrado = clean.invoke([HumanMessage(
        content = f"""Limpia el siguiente mail:\n
            {state["cuerpo"]}
        """
    )])
    if not hasattr(cuerpo_filtrado, "content"):
        raise AttributeError("El objeto retornado por clean.invoke no tiene el atributo 'content'.")
    return Input(asunto=state['asunto'], cuerpo=cuerpo_filtrado.content, adjuntos=state['adjuntos'])

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
