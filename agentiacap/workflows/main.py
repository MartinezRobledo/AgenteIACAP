from typing import Literal
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from agentiacap.agents.agentCleaner import cleaner
from agentiacap.agents.agentClassifier import classifier
from agentiacap.agents.agentExtractor import extractor
from agentiacap.configs.classes import Input, Output, Mail
import logging

logging.basicConfig(level=logging.ERROR)  # Puedes usar INFO, WARNING, etc.
logger = logging.getLogger("langchain")
logger.setLevel(logging.ERROR)

relevant_categories = ["Estado de facturas", "Pedido devolución retenciones", "Impresión de OP y/o Retenciones"]

async def call_cleaner(state: Input) -> Mail:
    cleaned_result = await cleaner.ainvoke(state)
    return {"asunto":cleaned_result["asunto"], "cuerpo":cleaned_result["cuerpo"], "adjuntos":cleaned_result["adjuntos"]}

async def call_classifier(state: Mail) -> Command[Literal["Extractor", "Output"]]:
    input_schema = Input(asunto=state["asunto"], cuerpo=state["cuerpo"], adjuntos=state["adjuntos"])
    classified_result = await classifier.ainvoke(input_schema)
    if classified_result["category"] in relevant_categories:
        goto = "Extractor"
    else:
        goto = "Output"
    return Command(
        update={"categoria": classified_result["category"]},
        goto=goto
    )

async def call_extractor(state: Mail) -> Mail:
    input_schema = Input(asunto=state["asunto"], cuerpo=state["cuerpo"], adjuntos=state["adjuntos"])
    extracted_result = await extractor.ainvoke(input_schema)
    return {"extracciones": extracted_result["extractions"], "tokens": extracted_result["tokens"]}

def output_node(state: Mail) -> Output:
    result = {
        "category": state["categoria"],
        "extractions": state["extracciones"],
        "tokens": state["tokens"]
    }
    return {"result": result}

# Workflow principal
builder = StateGraph(Mail, input=Input, output=Output)

builder.add_node("Cleaner", call_cleaner)
builder.add_node("Classifier", call_classifier)
builder.add_node("Extractor", call_extractor)
builder.add_node("Output", output_node)

builder.add_edge(START, "Cleaner")
builder.add_edge("Cleaner", "Classifier")
builder.add_edge("Extractor", "Output")
builder.add_edge("Output", END)


graph = builder.compile()