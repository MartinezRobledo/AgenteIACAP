from asyncio.log import logger
from langgraph.graph import StateGraph, START, END
from agentiacap.agents.agentExtractor import extractor
from agentiacap.utils.globals import InputSchema, MailSchema, OutputSchema, generate_message, obtener_facturas, obtener_valor_por_prioridad

def generar_resumen(datos):
    extractions = datos.get("extracciones", [])
    fuentes_prioritarias = ["Mail", "Document Intelligence", "Vision"]
    customer = obtener_valor_por_prioridad(extractions, "CustomerName", fuentes_prioritarias)
    cod_soc = obtener_valor_por_prioridad(extractions, "CustomerCodSap", fuentes_prioritarias)
    resume = {
        "CUIT": obtener_valor_por_prioridad(extractions, "VendorTaxId", fuentes_prioritarias),
        "Proveedor": obtener_valor_por_prioridad(extractions, "VendorName", fuentes_prioritarias),
        "Sociedad": customer,
        "Cod_Sociedad": cod_soc,
        "Facturas": obtener_facturas(extractions)
    }

    return resume

def faltan_datos_requeridos(resume):
    
    required_fields = ["CUIT", "Sociedad"]
    
    # Verifica si falta algún campo requerido o está vacío
    falta_campo_requerido = any(not resume.get(field) for field in required_fields)

    # Verifica si no hay fecha de trasferencia
    falta_fecha = not [f["Fecha"] and f["Monto"] for f in resume["Facturas"] if f["Fecha"] != '']

    return falta_campo_requerido or falta_fecha

async def call_extractor(state: MailSchema) -> MailSchema:
    try:
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo_original"], adjuntos=state["adjuntos"])
        extracted_result = await extractor.ainvoke(input_schema)
        return {"extracciones": extracted_result["extractions"], "tokens": extracted_result["tokens"]}
    except Exception as e:
        logger.error(f"Error en 'call_extractor': {str(e)}")
        raise

def resumen_impresion_op(state: MailSchema) -> OutputSchema:
    try:
        is_missing_data = False
        resume = generar_resumen(state)
        print("Resumen generado...", resume)
        is_missing_data = faltan_datos_requeridos(resume)
        message = ""
        if is_missing_data:
                message = generate_message(state.get("cuerpo"),
                            {
                                "CUIT": resume["CUIT"], 
                                "Sociedad": resume["Sociedad"],
                                "Fecha de transeferencia": [f["Fecha"] for f in resume["Facturas"]],
                                "Montos": [f["Monto"] for f in resume["Facturas"]]
                            }
                        )

        result = {
            "categoria": "Impresión de OP y/o Retenciones",
            "extractions": state.get("extracciones", []),
            "tokens": state.get("tokens", 0),
            "resume": resume,
            "is_missing_data": is_missing_data,
            "message": message
        }
        return {"result": result}
        
    except Exception as e:
        logger.error(f"Error en 'output_node': {str(e)}")
        raise

builder = StateGraph(input=MailSchema, output=OutputSchema)

builder.add_node("Extractor", call_extractor)
builder.add_node("impresion_op", resumen_impresion_op)

builder.add_edge(START, "Extractor")
builder.add_edge("Extractor", "impresion_op")
builder.add_edge("impresion_op", END)

graph = builder.compile()