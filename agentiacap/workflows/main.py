import logging
from typing import Literal
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from agentiacap.agents.agentCleaner import cleaner
from agentiacap.agents.agentClassifier import classifier
from agentiacap.agents.agentExtractor import extractor
from agentiacap.utils.globals import InputSchema, OutputSchema, MailSchema, relevant_categories, lista_sociedades
from agentiacap.llms.llms import llm4o_mini

# Configuración del logger
logging.basicConfig(level=logging.INFO)
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

    def obtener_valor_por_prioridad(extractions, campo, fuentes_prioritarias):
        for fuente in fuentes_prioritarias:
            for extraccion in extractions:
                if extraccion["source"] == fuente:
                    for extraccion_data in extraccion["extractions"]:
                        for archivo, datos in extraccion_data.items():
                            for item in datos:
                                valor = item["fields"].get(campo)
                                if valor and valor.strip() and valor.lower() not in ["none", "", "-"]:  
                                    return valor.strip()  # Retorna el primer valor válido
        return None  # Si no encuentra nada válido, retorna None

    def obtener_facturas(extractions):
        facturas = []
        ids_vistos = set()
        fuentes_facturas = ["Document Intelligence", "Vision"]

        for fuente in fuentes_facturas:
            for extraccion in extractions:
                if extraccion["source"] == fuente:
                    for archivo, datos in extraccion["extractions"][0].items():
                        for item in datos:
                            invoice_id = item["fields"].get("InvoiceId")
                            invoice_date = item["fields"].get("InvoiceDate")

                            if invoice_id:
                                invoice_id = invoice_id.strip()
                            else:
                                invoice_id = ""

                            if invoice_date:
                                invoice_date = invoice_date.strip()
                            else:
                                invoice_date = ""
                            if invoice_id and invoice_id not in ids_vistos:
                                facturas.append({"ID": invoice_id, "Fecha": invoice_date})
                                ids_vistos.add(invoice_id)

        if not facturas:
            for extraccion in extractions:
                if extraccion["source"] == "Mail":
                    for archivo, datos in extraccion["extractions"][0].items():
                        for item in datos:
                            invoice_ids = item["fields"].get("InvoiceId", [])
                            if isinstance(invoice_ids, list):
                                for invoice_id in invoice_ids:
                                    if invoice_id not in ids_vistos:
                                        facturas.append({"ID": invoice_id, "Fecha": ""})
                                        ids_vistos.add(invoice_id)

        return facturas

    def get_codSap(customer):
        for soc in lista_sociedades:
            if soc.get("Nombre Soc SAP") == customer:
                return soc.get("Código SAP")
        return customer

    def generar_json(datos):
        extractions = datos.get("extracciones", [])
        fuentes_prioritarias = ["Mail", "Document Intelligence", "Vision"]

        json_generado = {
            "CUIT": obtener_valor_por_prioridad(extractions, "VendorTaxId", fuentes_prioritarias),
            "Sociedad": get_codSap(obtener_valor_por_prioridad(extractions, "CustomerName", fuentes_prioritarias)),
            "Factura": obtener_facturas(extractions)
        }

        return json_generado

    def faltan_datos_requeridos(resume):
        required_fields = ["CUIT", "Sociedad"]
        
        # Verifica si falta algún campo requerido o está vacío
        falta_campo_requerido = any(not resume.get(field) for field in required_fields)

        # Verifica si no hay facturas o si todas las facturas tienen una "Fecha" vacía
        falta_fecha_factura = not resume.get("Factura") or all(not factura.get("Fecha") for factura in resume["Factura"])

        return falta_campo_requerido or falta_fecha_factura

    def generate_message(cuerpo, category, resume):
        response = llm4o_mini.invoke(f"""-Eres un asistente que responde usando el estilo y tono de Argentina. Utiliza modismos argentinos y un lenguaje informal pero educado.
                                En base a este mail de entrada: {cuerpo}. 
                                Redactá un mail con la siguiente estructura:
 
                                Estimado, 
                                
                                Su caso ha sido catalogado como {category}. Para poder darte una respuesta necesitamos que nos brindes los siguientes datos:
                                CUIT
                                Sociedad de YPF a la que se facturó
                                Facturas (recordá mencionarlas con su numero completo 9999A99999999)
                                Fecha de las facturas
                                Montos
                                De tu consulta pudimos obtener la siguiente información:
                                <formatear el input para que sea legible y mantenga la manera de escribir que se viene usando en el mail>
                                {resume}
                                
                                En caso que haya algún dato incorrecto, por favor indicalo en tu respuesta.

                                Instrucciones de salida:
                                -Los datos faltantes aclaralos solamente como "sin datos". No uses "None" ni nada por el estilo.
                                -El mail lo va a leer una persona que no tiene conocimientos de sistemas. Solo se necesita el cuerpo del mail en html y no incluyas asunto en la respuesta.
                                -Firma siempre el mail con 'CAP - Centro de Atención a Proveedores YPF'.
                                 """)
        return response.content

    try:
        logging.info("Terminando respuesta...")
        resume = generar_json(state) 
        logging.info("Json generado...")
        category = state.get("categoria", "Desconocida")
        is_missing_data = faltan_datos_requeridos(resume)
        message = ""
        if is_missing_data:
            message = generate_message(state.get("cuerpo"), category, resume)

        result = {
            "category": category,
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
