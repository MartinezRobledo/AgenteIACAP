import logging
from typing import Literal
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from agentiacap.agents.agentCleaner import cleaner
from agentiacap.agents.agentClassifier import classifier
from agentiacap.agents.agentExtractor import extractor
from agentiacap.utils.globals import InputSchema, OutputSchema, MailSchema, relevant_categories

# Configuración del logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

async def call_cleaner(state: InputSchema) -> MailSchema:
    try:
        cleaned_result = await cleaner.ainvoke(state)
        return {"asunto":cleaned_result["asunto"], "cuerpo":cleaned_result["cuerpo"], "adjuntos":cleaned_result["adjuntos"]}
    except Exception as e:
        logger.error(f"Error en 'call_cleaner': {str(e)}")
        raise

async def call_classifier(state: MailSchema) -> Command[Literal["Extractor", "Output"]]:
    try:
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo"], adjuntos=state["adjuntos"])
        classified_result = await classifier.ainvoke(input_schema)
        if classified_result["category"] in relevant_categories:
            goto = "Extractor"
        else:
            goto = "Output"
        return Command(
            update={"categoria": classified_result["category"]},
            goto=goto
        )
    except Exception as e:
        logger.error(f"Error en 'call_classifier': {str(e)}")
        raise

async def call_extractor(state: MailSchema) -> MailSchema:
    try:
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo"], adjuntos=state["adjuntos"])
        extracted_result = await extractor.ainvoke(input_schema)
        return {"extracciones": extracted_result["extractions"], "tokens": extracted_result["tokens"]}
    except Exception as e:
        logger.error(f"Error en 'call_extractor': {str(e)}")
        print(f"Error en 'call_extractor': {str(e)}")
        raise

def output_node(state: MailSchema) -> OutputSchema:
    try:
        result = {
            "category": state.get("categoria", "Desconocida"),
            "extractions": state.get("extracciones", []),  # Valor por defecto: diccionario vacío
            "tokens": state.get("tokens", 0)  # Valor por defecto: 0
        }
        return {"result": result}
    except Exception as e:
        logger.error(f"Error en 'output_node': {str(e)}")
        raise


# Workflow principal
builder = StateGraph(MailSchema, input=InputSchema, output=OutputSchema)

builder.add_node("Cleaner", call_cleaner)
builder.add_node("Classifier", call_classifier)
builder.add_node("Extractor", call_extractor)
builder.add_node("Output", output_node)

builder.add_edge(START, "Cleaner")
builder.add_edge("Cleaner", "Classifier")
builder.add_edge("Extractor", "Output")
builder.add_edge("Output", END)

graph = builder.compile()
