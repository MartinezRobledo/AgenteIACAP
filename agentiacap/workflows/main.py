import logging
from typing import Literal
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from agentiacap.agents.agentCleaner import cleaner
from agentiacap.agents.agentClassifier import classifier
from agentiacap.utils.globals import InputSchema, OutputSchema, MailSchema
from agentiacap.workflows import devolucion_retenciones, estado_facturas, impresion_op

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def call_cleaner(state: InputSchema) -> MailSchema:
    try:
        cleaned_result = await cleaner.ainvoke(state)
        return {"asunto":cleaned_result["asunto"], "cuerpo":cleaned_result["cuerpo"], "adjuntos":cleaned_result["adjuntos"], "cuerpo_original":state["cuerpo"]}
    except Exception as e:
        logger.error(f"Error en 'call_cleaner': {str(e)}")
        raise

async def call_classifier(state: MailSchema) -> Command[Literal["estado_facturas", "impresion_op", "devolucion_retenciones", "output_node"]]:
    try:
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo"], adjuntos=state["adjuntos"])
        classified_result = await classifier.ainvoke(input_schema)

        if classified_result["categoria"] == "Estado de facturas":
            goto = "estado_facturas"
        elif classified_result["categoria"] == "Impresión de OP y/o Retenciones":
            goto = "impresion_op"
        elif classified_result["categoria"] == "Pedido devolución retenciones":
            goto = "devolucion_retenciones"
        else:
            goto = "output_node"

        return Command(
            update={"categoria": classified_result["categoria"]},
            goto=goto
        )
    except Exception as e:
        logger.error(f"Error en 'call_classifier': {str(e)}")
        raise



async def call_estado_facturas(state:MailSchema) -> MailSchema:
    try:
        return await estado_facturas.graph.ainvoke(state)
    except Exception as e:
        logger.error(f"Error en Nodo 'estado_facturas': {str(e)}")
        raise

async def call_impresion_op(state:MailSchema) -> MailSchema:
    try:
        return await impresion_op.graph.ainvoke(state)
    except Exception as e:
        logger.error(f"Error en Nodo 'impresion_op': {str(e)}")
        raise

async def call_devolucion_retenciones(state:MailSchema) -> MailSchema:
    try:
        return await devolucion_retenciones.graph.ainvoke(state)
    except Exception as e:
        logger.error(f"Error en 'devolución_retenciones': {str(e)}")
        raise

def output_node(state: MailSchema) -> OutputSchema:
        return {"result": state}

# Workflow principal
builder = StateGraph(MailSchema, input=InputSchema, output=OutputSchema)

builder.add_node("Cleaner", call_cleaner)
builder.add_node("Classifier", call_classifier)
builder.add_node("estado_facturas", call_estado_facturas)
builder.add_node("impresion_op", call_impresion_op)
builder.add_node("devolucion_retenciones", call_devolucion_retenciones)
builder.add_node("output_node", output_node)

builder.add_edge(START, "Cleaner")
builder.add_edge("Cleaner", "Classifier")
builder.add_edge("estado_facturas", END)
builder.add_edge("impresion_op", END)
builder.add_edge("devolucion_retenciones", END)
builder.add_edge("output_node", END)

graph = builder.compile()
