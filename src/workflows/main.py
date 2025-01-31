from langgraph.graph import StateGraph, START, END, MessagesState
from src.agents.agentCleaner import cleaner
from src.agents.agentClassifier import classifier
from src.agents.agentExtractor import extractor
from src.configs.classes import Input, Output


# Workflow principal
builder = StateGraph(input=Input, output=Output)
builder.add_node("Cleaner", cleaner)
builder.add_node("Classifier", classifier)
builder.add_node("Extractor", extractor)


builder.add_edge(START, "Cleaner")
builder.add_edge("Cleaner", "Classifier")
# builder.add_edge("Classifier", "Extractor")
builder.add_edge("Classifier", END)


graph = builder.compile()