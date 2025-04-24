from asyncio.log import logger
from agentiacap.tools.convert_pdf import pdf_binary_to_images_base64
from agentiacap.tools.document_intelligence import ImageFieldExtractor
from agentiacap.utils.globals import MailSchema, OutputSchema
from agentiacap.workflows.responser import responder_mail_retenciones
from agentiacap.agents.agentExtractor import extractor
from langgraph.graph import StateGraph, START, END
from agentiacap.utils.globals import InputSchema, MailSchema, OutputSchema, generate_message, obtener_facturas, obtener_valor_por_prioridad


async def call_extractor(state: MailSchema) -> MailSchema:
    try:
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo_original"], adjuntos=state["adjuntos"])
        extracted_result = await extractor.ainvoke(input_schema)
        return {"extracciones": extracted_result["extractions"], "tokens": extracted_result["tokens"]}
    except Exception as e:
        logger.error(f"Error en 'call_extractor': {str(e)}")
        raise

def faltan_datos_requeridos(resume):
        
    required_fields = ["CUIT", "Sociedad"]
    
    # Verifica si falta algún campo requerido o está vacío
    falta_campo_requerido = any(not resume.get(field) for field in required_fields)

    # Verifica si no hay facturas
    falta_factura = not resume.get("Facturas")

    return falta_campo_requerido or falta_factura
    
def clasificar_extraccion_retenciones(data):
    resultado = {
        "nota_modelo": [],
        "certificado_retenciones": []
    }

    for item in data:
        info = {
            "file_name": item["file_name"],
            "firmada": item["extractions"]["firmada"],
            "datos_completos": item["extractions"]["datos_completos"],
            "datos": item["extractions"]["datos"]
        }

        if item["extractions"]["es_nota_modelo"]:
            resultado["nota_modelo"].append(info)
        elif item["extractions"]["es_certificado_retenciones"]:
            resultado["certificado_retenciones"].append(info)

    return resultado

def validar_extracciones_retenciones(clasificado):
    notas = clasificado.get("nota_modelo", [])
    certificados = clasificado.get("certificado_retenciones", [])

    notas_completas = [n["file_name"] for n in notas if n["datos_completos"]]
    notas_incompletas = [n["file_name"] for n in notas if not n["datos_completos"]]

    certificados_completos = [c["file_name"] for c in certificados if c["datos_completos"]]
    certificados_incompletos = [c["file_name"] for c in certificados if not c["datos_completos"]]

    # Buscar proveedor y CUIT
    fuente_valida = next(
        (n for n in notas if n["datos_completos"]),
        next((c for c in certificados if c["datos_completos"]), None)
    )
    proveedor = fuente_valida["datos"]["nombre_proveedor"] if fuente_valida else ""
    cuit = fuente_valida["datos"]["CUIT_proveedor"] if fuente_valida else ""

    resultado = {
        "hay_nota_modelo": bool(notas),
        "hay_certificado_retenciones": bool(certificados),
        "certificados_completos": len(certificados_incompletos) == 0 and bool(certificados),
        "notas_modelo_completas": notas_completas,
        "notas_modelo_incompletas": notas_incompletas,
        "certificados_completos": certificados_completos,
        "certificados_incompletos": certificados_incompletos,
        "proveedor": proveedor,
        "cuit": cuit,
    }

    return resultado

def devolucion_retenciones(state: MailSchema) -> OutputSchema:
    try:
        images_from_pdfs = []
        for file in state["adjuntos"]:
            file_name = file["file_name"]
            if file_name.endswith(".pdf"):
                content = file.get("content", b"")
                pages = pdf_binary_to_images_base64(content, dpi=300)
                for page in pages:
                    page_name = page["file_name"]
                    image = {
                        "file_name": f"{file_name}-{page_name}",
                        "content": page["content"]
                    }
                    images_from_pdfs.append(image)
        extractions = []
        if images_from_pdfs:
            extractor = ImageFieldExtractor()
            extractions = extractor.es_carta_modelo(base64_images=images_from_pdfs)
        else:
            result = []

        is_missing_data = False
        clasificado = clasificar_extraccion_retenciones(extractions)
        resume = validar_extracciones_retenciones(clasificado)
        message = responder_mail_retenciones(resume, extractions)

        is_missing_data = (
            bool(resume["notas_modelo_incompletas"]) 
            or bool(resume["certificados_incompletos"]) 
            or not resume["hay_nota_modelo"] 
            or not resume["hay_certificado_retenciones"]
        )

        result = {
            "categoria": "Pedido devolución retenciones",
            "extractions": extractions,
            "tokens": 0,
            "resume": resume,
            "is_missing_data": is_missing_data,
            "message": message
        }
        return {"result": result}
    
    except Exception as e:
        logger.error(f"Error en 'output_node': {str(e)}")
        raise

builder = StateGraph(input=MailSchema, output=OutputSchema)

builder.add_node("extractor", call_extractor)
builder.add_node("devolucion_retenciones", devolucion_retenciones)

# builder.add_edge(START, "extractor")
builder.add_edge(START, "devolucion_retenciones")
# builder.add_edge("extractor", "devolucion_retenciones")
builder.add_edge("devolucion_retenciones", END)

graph = builder.compile()