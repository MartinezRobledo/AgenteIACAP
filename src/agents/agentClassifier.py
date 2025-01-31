import re
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from src.configs.llms import llm4o
from src.configs.classes import Input, Output
from src.configs.Prompt_Template import categories, reflection_definition, classifier_definition
from src.services.tools.evaluar_contexto import evaluar_contexto

categories = "\n".join(categories)

classification = classifier_definition | llm4o
llm_with_tools = reflection_definition | llm4o.bind_tools([evaluar_contexto])

def input_node(state:Input) -> MessagesState:
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
    ]}

async def classifier_node(state:MessagesState) -> MessagesState:
    result = await classification.ainvoke(state["messages"])
    return {"messages": [HumanMessage(content=result.content)]}

async def reflection_node(state: MessagesState) -> MessagesState:
    prompt = HumanMessage(
            content="""¿Es la categoría asignada coherente con el contexto del email? Para validar esto utilizá la tool 'evaluar contexto'.
            """
        )
    response = llm_with_tools.invoke(state["messages"]+[prompt])
    return {"messages": state["messages"]+[response]}

def output_node(state: MessagesState) -> Output:
    match = re.search(r"APROBADA:\s*\"([^\"]+)\"", state["messages"][-1].content)
    if match:
        categoria = match.group(1)  # Extraer el valor después de "APROBADA:"
        return Output(categoria=categoria, data={})
    return Output(categoria="Otras consultas", data={})  # Valor por defecto si no se logró aprobar la categoría.

# Defino edges
def should_continue(state: MessagesState) -> str:
    if "APROBADA" in state["messages"][-1].content:
        return "output"  # Si está aprobada, avanza al nodo output
    else:
        return "classifier"  # Si está rechazada, regresa al clasificador

# Defino grafo
builder = StateGraph(MessagesState, input=Input, output=Output)

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