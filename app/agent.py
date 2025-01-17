from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# Define el estado del agente
class State(TypedDict):
    my_var: str
    customer_name:str

# Defino nodes

def node_1(state: State) -> State:
    state["my_var"] = "Hello"
    state["customer_name"] = "CAP"
    return state

def node_2(state: State) -> State:
    state["my_var"] = f"Hello Adrián"
    return state

def node_3(state: State) -> State:
    return state

# Defino edges


# Defino graph
graph = StateGraph(State)

graph.add_node('node_1', node_1)
graph.add_node('node_2', node_2)
graph.add_node('node_3', node_3)


graph.add_edge(START, 'node_1')
graph.add_edge('node_1', 'node_2')
graph.add_edge('node_2', 'node_3')
graph.add_edge('node_3', END)


react = graph.compile()