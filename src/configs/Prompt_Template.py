from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

categories = [
    "Categoría: Alta de usuario, Descripción: Se suele pedir explícitamente en el asunto o en el cuerpo del mail. Sujeto a palabras claves dentro del contexto de la generación o gestión de un nuevo usuario.",
    "Categoría: Error de registración, Descripción: el reclamo siempre es por fechas de vencimiento mal aplicadas. Sujeto al contexto en que el proveedor reclama una mala asignación de la fecha de vencimiento de su factura en el sistema.", 
    "Categoría: Estado de facturas, Descripción: Consultas sobre estado de facturas, facturas pendientes, facturas vencidas, facturas impagas, facturas no cobradas.",
    "Categoría: Facturas rechazadas, Descripción: Se suele aclarar explícitamente en el asunto o en el cuerpo del mail que la factura fue rechazada. Sujeto a contexto en que se pide motivo del rechazo de una factura.", 
    "Categoría: Impresión de NC/ND, Descripción: Ahora se llama “Multas”. Sujeto a palabras clave relacionadas con Multas. Sujeto al contexto en que se reclama o consulta por diferencias en el pago . ", 
    "Categoría: Impresión de OP y/o Retenciones, Descripción: Suele ser una solicitud o pedido de ordenes de pago (OP) o retenciones. Suele estar explicito en el asunto o en el cuerpo del mail un mensaje pidiendo retenciones/OP.",
    "Categoría: Pedido devolución retenciones, Descripción: Suele estar explicito en el asunto o cuerpo del mail. Sujeto a palabras clave relacionadas con una devolución o reintegro de una retención. También se suele hacer mención con frecuencia que se envía una nota o se adjunta una nota solicitando a la devolución del monto retenido.",
    "Categoría: Presentación de facturas, Descripción: Sujeto al contexto en que el proveedor adjunta una factura y aclara el numero de la factura. Puede explicitar que es una presentación en el asunto como puede no hacerlo, pero siempre se va a referir a un mensaje que indica el adjunto de una factura. Esta no es una categoría en la que entren consultas.", 
    "Categoría: Problemas de acceso, Descripción: Sujeto al contexto en que se reclama por no poder acceder a facturar u obtener información de una factura. No se solicita información de una factura solo se reclama el acceso al sistema.", 
    "Categoría: Salientes YPF, Descripción: No se aclara explícitamente el texto “Salientes YPF”. Está sujeto al contexto en que se pide INFORMAR AL PROVEEDOR de algo."
    "Categoría: Otras consultas, Descripción: Consultas generales que no encajan en ninguna de las categorías."
]

fields_to_extract = [
    "VendorName",
    "CustomerName",
    "CustomerTaxId",
    "VendorTaxId",
    "CustomerAddress",
    "InvoiceId",
    "InvoiceDate",
    "InvoiceTotal",
]

# Instruccion del agente de limpieza
cleaner_definition = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Eres un agente especializado en limpiar correos electrónicos. Tu tarea es extraer únicamente la conversación relevante entre las partes involucradas (como preguntas, respuestas y comentarios útiles). Debes eliminar todo lo que no sea parte de la conversación directa, incluyendo:

            Firmas automáticas (nombre, cargo, empresa, teléfonos, etc.).
            Cabeceras de correo (como "De:", "Para:", "Asunto:", "Enviado:").
            Respuestas previas repetidas en cadenas largas de correos.
            Publicidad, disclaimers legales, y pie de página.
            Texto decorativo o irrelevante (como saludos genéricos y despedidas excesivamente largas).
            Reglas para procesar el email:

            Conserva solo el intercambio de mensajes relevante entre las partes.
            Mantén el texto legible y organizado en un formato limpio.
            No alteres el contenido relevante ni lo parafrasees.
            Ignora elementos irrelevantes como saludos triviales o cortesías sin importancia.
            Devuelve el resultado como un bloque de texto claro y organizado.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Instruccion del agente clasificador
classifier_definition = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Sos un categorizador de casos que se reciben por mail de un contact center de un equipo de facturación. 
            Vas a recibir un asunto y un cuerpo de un mail y tenés que categorizarlo en base a las categorías que te indiquen.
            La respuesta solo puede ser alguna de las opciones posibles para categorizar un mail y te vas a basar en la descripción de la categoría para hacerlo.
            La respuesta que des tiene que incluir el mail que recibiste para analizar y la categoría que terminaste eligiendo.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Instruccion del agente reflexivo
reflection_definition = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Eres un asistente experto en análisis de texto y validación de clasificaciones. 
            Tu tarea es validar si el mail que se te brinda junto con su categoría asignada es coherente con su descripción.
            Para esto vas a hacer uso de las categorías y descripciones que se te brinden. 
            Si la categoría no es adecuada, deberás explicar por qué al modelo que categoriza para que pueda encontrar una mejor categoría.
            Tienes que tener en cuenta que los mensajes pueden venir ambiguos o con información faltante, y tambien pueden no encajar en ninguna categoría, en esos casos debe ser 'Otras consultas'.""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

cleaner_prompt = {
    "messages": 
        [
            HumanMessage(
                content=f"""A continuación te dejo el siguiente mail para que lo categorices,\n
                Asunto: {'state._asunto'}.\n 
                Cuerpo: {'cuerpo_filtrado'}.\n 
                Las categorias posibles son:\n
                {categories}
                Si te parece que no aplica ninguna o la información parece incompleta entonces categorizalo como 'Otras consultas'."""
            )
        ]
}

# Prompt que se incorpora a la reflexion
reflection_prompt = HumanMessage(
            content = f"""¿Es la categoria asignada coherente con el contexto del mensaje? 
            Si es que SI aclara en la respuesta 'GO TO END: "Categoría asignada"' donde categoría asignada es la categoría que se genero como respuesta.
            Si es que NO el texto 'GO TO END' NO debe aparecer en el mensaje de salida.
            Las categorias posibles son:\n
            {categories}
            """
)

text_extractor_definition = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""Eres una IA especializada en extracción de información de correos electrónicos. Se te proporcionaré el contenido de un email y una lista de datos específicos que necesito extraer.  

            **Instrucciones:**  
            - Analiza el contenido del correo y extrae la información solicitada.  
            - Si algún dato no está presente, indica "No encontrado".  
            - Responde en formato JSON con las claves de los datos solicitados y sus valores extraídos.  
            - Mantén el formato original de los valores y evita interpretaciones subjetivas.  

            **Lista de datos a extraer:**  
            {fields_to_extract}
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)