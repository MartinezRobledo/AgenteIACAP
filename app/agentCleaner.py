from typing import TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver

# Define the schema for the input
class State(TypedDict):
    cuerpo: str

# Instruccion del agente de limpieza
cleaner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an email cleaning agent. Your task is to process and clean the content of an email, extracting only the relevant conversation between the involved parties, removing any metadata, signatures, automatic responses, and any other non-essential text. The final output should be a clean email with the relevant content in a single continuous line of text, without any line breaks, tabs, extra spaces, or any other formatting. Do not provide any explanations or details about the process. Just return the cleaned conversation as a continuous block of text.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
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

# Defino nodes
def input_node(state: State) -> State:
    cuerpo_filtrado = clean.invoke([HumanMessage(
        content = f"""Limpia el siguiente mail:\n
            {state['cuerpo']}
        """
    )])
    return State(cuerpo = cuerpo_filtrado.content)

builder = StateGraph(State)
builder.add_node("input", input_node)
builder.add_edge(START, "input")
builder.add_edge("input", END)
graph = builder.compile()
