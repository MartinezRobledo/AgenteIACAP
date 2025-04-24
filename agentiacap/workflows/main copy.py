import json
import logging
from typing import Literal, Sequence
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from agentiacap.agents.agentCleaner import cleaner
from agentiacap.agents.agentClassifier import classifier
from agentiacap.agents.agentExtractor import extractor
from agentiacap.tools.convert_pdf import pdf_binary_to_images_base64
from agentiacap.tools.document_intelligence import ImageFieldExtractor
from agentiacap.utils.globals import InputSchema, OutputSchema, MailSchema, relevant_categories, lista_sociedades
from agentiacap.llms.llms import llm4o_mini
from agentiacap.workflows.responser import responder_mail_retenciones

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

async def call_classifier(state: MailSchema) -> Command[Literal["Extractor", "DevRetenciones", "Output"]]:
    try:
        input_schema = InputSchema(asunto=state["asunto"], cuerpo=state["cuerpo"], adjuntos=state["adjuntos"])
        classified_result = await classifier.ainvoke(input_schema)
        if classified_result["category"] in relevant_categories:
            goto = "Extractor"
        elif classified_result["category"] == "Pedido devolución retenciones":
            goto = "DevRetenciones"
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

async def DevRetencionesNode(state:MailSchema) -> MailSchema:
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
        if images_from_pdfs:
            extractor = ImageFieldExtractor()
            result = extractor.es_carta_modelo(base64_images=images_from_pdfs)
        else:
            result = []

        return {"extracciones": result}
    except Exception as e:
        logger.error(f"Error en 'DevRetencionesNode': {str(e)}")
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
        nulos = ["null", "none", "-"]
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
                                invoice_total = page["fields"].get("InvoiceTotal", None)
                                        
                                if invoice_id and invoice_id not in ids_vistos:
                                    if invoice_id not in nulos and invoice_date not in nulos:
                                        facturas.append({"Factura": invoice_id, "Fecha": invoice_date, "Monto": invoice_total})
                                        ids_vistos.add(invoice_id)

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
                            invoice_total = page["fields"].get("InvoiceTotal", [])  
                            # Itero segun la lista con mas elementos
                            if not invoice_id: invoice_id = []
                            if not invoice_date: invoice_date = []
                            if not invoice_total: invoice_total = []
                            max_length = max(max(len(invoice_id), len(invoice_date)), len(invoice_total))
                            for i in range(max_length):
                                invoice = invoice_id[i] if i < len(invoice_id) else ""
                                fecha = invoice_date[i] if i < len(invoice_date) else ""
                                monto = invoice_total[i] if i < len(invoice_total) else ""
                                facturas.append({"Factura": invoice, "Fecha": fecha, "Monto": monto})

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
    
    def faltan_datos_requeridos_op_ret(resume):
        
        required_fields = ["CUIT", "Sociedad"]
        
        # Verifica si falta algún campo requerido o está vacío
        falta_campo_requerido = any(not resume.get(field) for field in required_fields)

        # Verifica si no hay fecha de trasferencia
        falta_fecha = not [f["Fecha"] and f["Monto"] for f in resume["Facturas"] if f["Fecha"] != '']

        return falta_campo_requerido or falta_fecha

    def generate_message(cuerpo, resume):
        response = llm4o_mini.invoke(f"""-Eres un asistente que responde usando el estilo y tono de Argentina. Utiliza modismos argentinos y un lenguaje informal pero educado.
                                En base a este mail de entrada: {cuerpo}. 
                                Redactá un mail con la siguiente estructura:
 
                                Estimado, 
                                
                                Para poder darte una respuesta necesitamos que nos brindes los siguientes datos:
                                <Lista los valores de la siguiente lista (solamente lo valores de la lista, no infieras datos que no esten en la lista): {resume.keys()}. Si algun valor de esa lista es igual a 'Facturas' agrega debajo el detalle: *Facturas (recordá mencionarlas con su numero completo 9999A99999999). Si en la lista no hay un valor 'Facturas' no agregues este detalle>
                                
                                De tu consulta pudimos obtener la siguiente información:
                                <formatear el siguiente diccionario para que sea legible y mantenga la manera de escribir que se viene usando en el mail.>
                                {resume}
                                
                                En caso que haya algún dato incorrecto, por favor indicalo en tu respuesta.

                                Instrucciones de salida:
                                -Cuando sea necesario, quiero que me devuelvas el verbo sin el pronombre enclítico en la forma imperativa.
                                -Los datos faltantes aclaralos solamente como "sin datos". No uses "None" ni nada por el estilo.
                                -El mail lo va a leer una persona que no tiene conocimientos de sistemas. Solo se necesita el cuerpo del mail en html para que se pueda estructurar en Outlook y no incluyas asunto en la respuesta.
                                -No aclares que estas generando un mail de respuesta, solo brinda el mail.
                                -No generes un saludo de despedida ni una firma.
                                 """)
        return response.content
    
    def clasificar_extraccion_retenciones(data):
        resultado = {
            "nota_modelo": [],
            "certificado_retenciones": []
        }

        for item in data:
            info = {
                "file_name": item["file_name"],
                "firmada": item["firmada"],
                "datos_completos": item["datos_completos"],
                "datos": item["datos"]
            }

            if item.get("es_nota_modelo"):
                resultado["nota_modelo"].append(info)
            elif item.get("es_certificado_retenciones"):
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
            "cuit": cuit
        }

        return resultado


    try:
        print("Terminando respuesta...")
        category = state.get("categoria", "Desconocida")
        is_missing_data = False
        if category not in relevant_categories:
            if category == "Pedido devolución retenciones":
                extractions = state.get("extracciones", [])
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
                    "category": category,
                    "extractions": extractions,
                    "tokens": 0,
                    "resume": resume,
                    "is_missing_data": is_missing_data,
                    "message": message
                }
                return {"result": result}
            else:
                result = {
                    "category": category,
                    "extractions": state.get("extracciones", []),
                    "tokens": 0,
                    "resume": {},
                    "is_missing_data": False,
                    "message": ""
                }
                return {"result": result}
        
            resume = generar_resumen(state)
            print("Resumen generado...", resume)
            if category == "Impresión de OP y/o Retenciones":
                is_missing_data = faltan_datos_requeridos_op_ret(resume)
                message = ""
                if is_missing_data:
                        message = generate_message(state.get("cuerpo"),
                                    {
                                        "CUIT": resume["CUIT"], 
                                        "Sociedad": resume["Sociedad"],
                                        # "Facturas": [f["Factura"] for f in resume["Facturas"]],
                                        "Fecha de transeferencia": [f["Fecha"] for f in resume["Facturas"]],
                                        "Montos": [f["Monto"] for f in resume["Facturas"]]
                                    }
                                )
                else:
                    message = generate_message(state.get("cuerpo"),
                                {
                                    "CUIT": resume["CUIT"], 
                                    "Sociedad": resume["Sociedad"],
                                    "Facturas": [f["Factura"] for f in resume["Facturas"]]
                                }
                            )

            result = {
                "category": category,
                "extractions": state.get("extracciones", []),
                "tokens": state.get("tokens", 0),
                "resume": resume,
                "is_missing_data": is_missing_data,
                "message": message
            }
            return {"result": result}
        else:
            is_missing_data = faltan_datos_requeridos(resume)
            message = ""
            if is_missing_data:
                    message = generate_message(state.get("cuerpo"),
                                {
                                    "CUIT": resume["CUIT"], 
                                    "Sociedad": resume["Sociedad"],
                                    "Facturas": [f["Factura"] for f in resume["Facturas"]]
                                }
                            )
            else:
                message = generate_message(state.get("cuerpo"),
                            {
                                "CUIT": resume["CUIT"], 
                                "Sociedad": resume["Sociedad"],
                                "Facturas": [f["Factura"] for f in resume["Facturas"]]
                            }
                        )

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
builder.add_node("DevRetenciones", DevRetencionesNode)
builder.add_node("Output", output_node)

builder.add_edge(START, "Cleaner")
builder.add_edge("Cleaner", "Classifier")
builder.add_edge("Extractor", "Output")
builder.add_edge("DevRetenciones", "Output")
builder.add_edge("Output", END)

graph = builder.compile()
