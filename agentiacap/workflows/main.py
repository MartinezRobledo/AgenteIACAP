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
        return {"asunto":cleaned_result["asunto"], "cuerpo":cleaned_result["cuerpo"], "adjuntos":cleaned_result["adjuntos"], "cuerpo_original":state["cuerpo"]}
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
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo_original"], adjuntos=state["adjuntos"])
        extracted_result = await extractor.ainvoke(input_schema)
        return {"extracciones": extracted_result["extractions"], "tokens": extracted_result["tokens"]}
    except Exception as e:
        logger.error(f"Error en 'call_extractor': {str(e)}")
        raise

def output_node(state: MailSchema) -> OutputSchema:

    def obtener_valor_por_prioridad(extractions, campo, fuentes_prioritarias):
        for fuente in fuentes_prioritarias:
            #extractions es una lista con objetos por cada tipo de extraccion
            for extraccion in extractions:
                if extraccion["source"] == fuente:
                    #extraccion["extractions"] es una lista de objetos por cada documento procesado
                    for documents in extraccion["extractions"]:
                        #document es una lista de objetos por cada pagina extraida
                        for document in documents:
                            document_data = documents[document]
                            for page in document_data:
                                value = page["fields"].get(campo, None)
                                if value:
                                    value = value.strip() 
                                    if value.lower() not in ["none", "", "-", "null"]:
                                        return value  # Retorna el primer valor válido

        return None  # Si no encuentra nada válido, retorna None

    def obtener_facturas(extractions):
        facturas = []
        ids_vistos = set()
        fuentes_facturas = ["Document Intelligence", "Vision"]

        for fuente in fuentes_facturas:
            for extraccion in extractions:
                if extraccion["source"] == fuente:
                    #extraccion["extractions"] es una lista de objetos por cada documento procesado
                    for documents in extraccion["extractions"]:
                        #document es una lista de objetos por cada pagina extraida
                        for document in documents:
                            document_data = documents[document]
                            for page in document_data:
                                invoice_id = page["fields"].get("InvoiceId", None)
                                invoice_date = page["fields"].get("InvoiceDate", None)
                                        
                                if invoice_id and invoice_id not in ids_vistos:
                                    facturas.append({"ID": invoice_id, "Fecha": invoice_date})
                                    ids_vistos.add(invoice_id)

        if not facturas:
            for extraccion in extractions:
                if extraccion["source"] == "Mail":
                    #extraccion["extractions"] es una lista de objetos por cada documento procesado
                    for documents in extraccion["extractions"]:
                        #document es una lista de objetos por cada pagina extraida
                        for document in documents:
                            document_data = documents[document]
                            for page in document_data:
                                invoice_id = page["fields"].get("InvoiceId", [])
                                invoice_date = page["fields"].get("InvoiceDate", [])  
                                # Itero segun la lista con mas elementos
                                if not invoice_id: invoice_id = []
                                if not invoice_date: invoice_date = []
                                max_length = max(len(invoice_id), len(invoice_date))
                                for i in range(max_length):
                                    invoice = invoice_id[i] if i < len(invoice_id) else ""
                                    fecha = invoice_date[i] if i < len(invoice_date) else ""
                                    facturas.append({"ID": invoice, "Fecha": fecha})

        return facturas

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

        # Verifica si no hay facturas
        falta_factura = not resume.get("Facturas")

        return falta_campo_requerido or falta_factura

    def generate_message(cuerpo, resume):
        response = llm4o_mini.invoke(f"""-Eres un asistente que responde usando el estilo y tono de Argentina. Utiliza modismos argentinos y un lenguaje informal pero educado.
                                En base a este mail de entrada: {cuerpo}. 
                                Redactá un mail con la siguiente estructura:
 
                                Estimado, 
                                
                                Para poder darte una respuesta necesitamos que nos brindes los siguientes datos:
                                CUIT
                                Sociedad de YPF a la que se facturó
                                Facturas (recordá mencionarlas con su numero completo 9999A99999999)
                                Montos
                                De tu consulta pudimos obtener la siguiente información:
                                <formatear el input para que sea legible y mantenga la manera de escribir que se viene usando en el mail. No mencionar fechas. Listar los campos de forma legible>
                                {resume}
                                
                                En caso que haya algún dato incorrecto, por favor indicalo en tu respuesta.

                                Instrucciones de salida:
                                -Cuando sea necesario, quiero que me devuelvas el verbo sin el pronombre enclítico en la forma imperativa.
                                -Los datos faltantes aclaralos solamente como "sin datos". No uses "None" ni nada por el estilo.
                                -El mail lo va a leer una persona que no tiene conocimientos de sistemas. Solo se necesita el cuerpo del mail en html para que se pueda estructurar en Outlook y no incluyas asunto en la respuesta.
                                -Firma siempre el mail con 'CAP - Centro de Atención a Proveedores YPF'.
                                -No aclares que estas generando un mail de respuesta, solo brinda el mail.
                                 """)
        return response.content

    try:
        print("Terminando respuesta...")
        category = state.get("categoria", "Desconocida")

        if category not in relevant_categories:
            result = {
                "category": category,
                "extractions": [],
                "tokens": 0,
                "resume": {},
                "is_missing_data": False,
                "message": ""
            }
            return {"result": result}
        
        resume = generar_resumen(state) 
        print("Resumen generado...", resume)
        is_missing_data = faltan_datos_requeridos(resume)
        message = ""
        if is_missing_data:
            message = generate_message(state.get("cuerpo"),
                                       {"CUIT": resume["CUIT"], 
                                        "Sociedad": resume["Sociedad"],
                                        "Facturas": resume["Facturas"]
                                        })

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
