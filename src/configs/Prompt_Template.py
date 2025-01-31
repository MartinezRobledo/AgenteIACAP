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

lista_sociedades = [
    {"Nombre Soc SAP": "AESA", "Código SAP": "0478", "Estado": "Activa", "CUIT": "30685211890", "Nombre en AFIP": "ASTRA EVANGELISTA SA"},
    {"Nombre Soc SAP": "YPF GAS", "Código SAP": "0522", "Estado": "Activa", "CUIT": "33555234649", "Nombre en AFIP": "YPF GAS S.A."},
    {"Nombre Soc SAP": "UTE LA VENTANA", "Código SAP": "0571", "Estado": "Activa", "CUIT": "30652671418", "Nombre en AFIP": "YACIMIENTO LA VENTANA YPF SA SINOPEC ARGENTINA EXPLORATION AND PRODUCTION INC UNION TRANSITORIA"},
    {"Nombre Soc SAP": "YPF S.A.", "Código SAP": "0620", "Estado": "Activa", "CUIT": "30546689979", "Nombre en AFIP": "YPF SA"},
    {"Nombre Soc SAP": "Fundación YPF", "Código SAP": "0789", "Estado": "Activa", "CUIT": "30691548054", "Nombre en AFIP": "FUNDACION YPF"},
    {"Nombre Soc SAP": "UTE LLANCANELO", "Código SAP": "0797", "Estado": "Activa", "CUIT": "30707293809", "Nombre en AFIP": "CONTRATO DE UNION TRANSITORIA DE EMPRESAS - AREA LLANCANELO U.T.E."},
    {"Nombre Soc SAP": "OPESSA", "Código SAP": "0680", "Estado": "Activa", "CUIT": "30678774495", "Nombre en AFIP": "OPERADORAS DE ESTACIONES DE SERVICIO SA"},
    {"Nombre Soc SAP": "UTE CAMPAMENTO CENTRAL CAÑADON PERDIDO", "Código SAP": "0862", "Estado": "Activa", "CUIT": "33707856349", "Nombre en AFIP": "YPF S A - SIPETROL ARGENTINA S A - UTE CAMPAMENTO CENTRAL - CAÑADON PERDIDO"},
    {"Nombre Soc SAP": "UTE BANDURRIA", "Código SAP": "0900", "Estado": "Activa", "CUIT": "30708313587", "Nombre en AFIP": "YPF S.A WINTENSHALL ENERGIA SA - PAN AMERICAN ENERGY LLC AREA BANDURRIA UTE"},
    {"Nombre Soc SAP": "Ute Santo Domingo I y II", "Código SAP": "0901", "Estado": "Activa", "CUIT": "30713651504", "Nombre en AFIP": "GAS Y PETROELO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA - YPF S.A. - AREA SANTO DOMINGO I Y II UTE"},
    {"Nombre Soc SAP": "UTE CERRO LAS MINAS", "Código SAP": "0918", "Estado": "Activa", "CUIT": "30712188061", "Nombre en AFIP": "GAS Y PETROLEO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA-YPF S.A.-TOTAL AUSTRAL SA SUC ARG-ROVELLA ENERGIA SA-AREA CERRO LAS MINAS UTE"},
    {"Nombre Soc SAP": "UTE ZAMPAL OESTE", "Código SAP": "1046", "Estado": "Activa", "CUIT": "30709441945", "Nombre en AFIP": "YPF S.A EQUITABLE RESOURCES ARGENTINA COMPANY S.A - ZAMPAL OESTE UTE"},
    {"Nombre Soc SAP": "UTE ENARSA 1", "Código SAP": "1146", "Estado": "Activa", "CUIT": "30710916833", "Nombre en AFIP": "ENERGIA ARGENTINA S.A.- YPF S.A.- PETROBRAS ENERGIA S.A.- PETROURUGUAY S.A. UNION TRANSITORIAS DE EMPRESAS E1"},
    {"Nombre Soc SAP": "UTE GNL ESCOBAR", "Código SAP": "1153", "Estado": "Activa", "CUIT": "30711435227", "Nombre en AFIP": "ENERGIA ARGENTINA S.A. - YPF S.A. - PROYECTO GNL ESCOBAR - UNION TRANSITORIA DE EMPRESAS"},
    {"Nombre Soc SAP": "UTE RINCON DEL MANGRULLO", "Código SAP": "1160", "Estado": "Activa", "CUIT": "30714428469", "Nombre en AFIP": "YPF S.A - PAMPA ENERGIA S.A.. UNION TRANSITORIA DE EMPRESAS - RINCON DEL MANGRULLO"},
    {"Nombre Soc SAP": "UTE CHACHAHUEN", "Código SAP": "1164", "Estado": "Activa", "CUIT": "30716199025", "Nombre en AFIP": "YPF S.A.-KILWER S.A.-KETSAL S.A.-ENERGIA MENDOCINA S.A. AREA CHACHAHUEN UNION TRANSITORIA DE EMPRESAS"},
    {"Nombre Soc SAP": "UTE LA AMARGA CHICA", "Código SAP": "1167", "Estado": "Activa", "CUIT": "30714869759", "Nombre en AFIP": "YPF S.A. - PETRONAS E&P ARGENTINA S.A."},
    {"Nombre Soc SAP": "UTE EL OREJANO", "Código SAP": "1169", "Estado": "Activa", "CUIT": "30715142658", "Nombre en AFIP": "YPF S.A.- PBB POLISUR S.A., AREA EL OREJANO UNION TRANSITORIA"},
    {"Nombre Soc SAP": "CIA HIDROCARBURO NO CONVENCIONAL SRL", "Código SAP": "1171", "Estado": "Activa", "CUIT": "30714124427", "Nombre en AFIP": "COMPAÑIA DE HIDROCARBURO NO CONVENCIONAL S.R.L."},
    {"Nombre Soc SAP": "UTE PAMPA (YSUR)", "Código SAP": "1632", "Estado": "Activa", "CUIT": "30711689067", "Nombre en AFIP": "APACHE ENERGIA ARGENTINA S.R.L. - PETROLERA PAMPA S.A., UNION TRANSITORIA DE EMPRESAS - ESTACION FERNANDEZ ORO Y ANTICLINAL CAMPAMENTO"}
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

lista_strings = [
    str({f'"""{key}"""': f'"{value}"' for key, value in sociedad.items()})
    for sociedad in lista_sociedades
]
lista_strings = "\n".join(lista_strings)

class TextExtractorPrompt:
    fields_to_extract_text = [
    "CustomerName: Este campo se refiere a la sociedad por la que se hace la consulta. Solo se pueden incluir las sociedades permitidas en la lista de sociedades.",
    "CustomerTaxId: Este campo se refiere al numero CUIT de la sociedad de YPF por la que se hace la consulta.",
    """InvoiceId: Este campo hace referencia al numero de factura por la que se hace la consulta. 
                A la factura se la puede mencionar como documento, comprobante, certificado, FC, FCA, FCE, FEA.""",
    "VendorTaxId: Este campo corresponde al numero CUIT de la persona o sociedad que envía la consulta.",
    "CAPCase: Este campo es el numero de caso del mail abierto en el CRM del centro de atencion a proveedores (CAP). El formato generalmente es asi YPF-CAP:0579000158, pero puede tener variaciones."
    ]
    fields_to_extract_text = "\n".join(fields_to_extract_text)
    text_extractor_definition = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""Eres una IA especializada en extracción de datos de correos electrónicos. Se te proporcionaré el contenido de un email y una lista de datos específicos que se necesita extraer.  

            **Instrucciones:**  
            - Analiza el contenido del correo y extrae la información solicitada.  
            - Los datos que se logran extraer van a formar parte de un array del campo 'fields'.
            - El numero de factura generalmente se menciona de forma explicita, pero en el caso de no estar de esa forma intenta encontrar un numero escondido que cumpla con el formato de 4 digitos seguidos de una letra 'A' o un caracter '-' seguido de 8 digitos mas.
            - Los datos que NO se logran extraer van a formar parte de un array del campo 'missing_fields'.
            - Los datos que estan dentro de 'missing_fields' no poseen valor por lo que solo se indica el nombre del campo.
            - Los datos se pueden encontrar tanto en el cuerpo como en el asunto del mail.
            - Los numero CUIT cumplen con el formato de 11 digitos numericos donde tanto los primeros 2 como el ultimo pueden estar separados del resto mediante un caracter '-' o un espacio.
            - Responde en formato JSON con las claves de los datos solicitados y sus valores extraídos.
            - Mantén el formato original de los valores y evita interpretaciones subjetivas.

            **Lista de datos a extraer:**  
            {fields_to_extract_text}

            **Lista de sociedades permitidas:
                -"Nombre Soc SAP": "AESA", "Código SAP": "0478", "Estado": "Activa", "CUIT": "30685211890", "Nombre en AFIP": "ASTRA EVANGELISTA SA"
                -"Nombre Soc SAP": "YPF GAS", "Código SAP": "0522", "Estado": "Activa", "CUIT": "33555234649", "Nombre en AFIP": "YPF GAS S.A."
                -"Nombre Soc SAP": "UTE LA VENTANA", "Código SAP": "0571", "Estado": "Activa", "CUIT": "30652671418", "Nombre en AFIP": "YACIMIENTO LA VENTANA YPF SA SINOPEC ARGENTINA EXPLORATION AND PRODUCTION INC UNION TRANSITORIA"
                -"Nombre Soc SAP": "YPF S.A.", "Código SAP": "0620", "Estado": "Activa", "CUIT": "30546689979", "Nombre en AFIP": "YPF SA",
                -"Nombre Soc SAP": "Fundación YPF", "Código SAP": "0789", "Estado": "Activa", "CUIT": "30691548054", "Nombre en AFIP": "FUNDACION YPF",
                -"Nombre Soc SAP": "UTE LLANCANELO", "Código SAP": "0797", "Estado": "Activa", "CUIT": "30707293809", "Nombre en AFIP": "CONTRATO DE UNION TRANSITORIA DE EMPRESAS - AREA LLANCANELO U.T.E.",
                -"Nombre Soc SAP": "OPESSA", "Código SAP": "0680", "Estado": "Activa", "CUIT": "30678774495", "Nombre en AFIP": "OPERADORAS DE ESTACIONES DE SERVICIO SA",
                -"Nombre Soc SAP": "UTE CAMPAMENTO CENTRAL CAÑADON PERDIDO", "Código SAP": "0862", "Estado": "Activa", "CUIT": "33707856349", "Nombre en AFIP": "YPF S A - SIPETROL ARGENTINA S A - UTE CAMPAMENTO CENTRAL - CAÑADON PERDIDO",
                -"Nombre Soc SAP": "UTE BANDURRIA", "Código SAP": "0900", "Estado": "Activa", "CUIT": "30708313587", "Nombre en AFIP": "YPF S.A WINTENSHALL ENERGIA SA - PAN AMERICAN ENERGY LLC AREA BANDURRIA UTE",
                -"Nombre Soc SAP": "Ute Santo Domingo I y II", "Código SAP": "0901", "Estado": "Activa", "CUIT": "30713651504", "Nombre en AFIP": "GAS Y PETROELO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA - YPF S.A. - AREA SANTO DOMINGO I Y II UTE",
                -"Nombre Soc SAP": "UTE CERRO LAS MINAS", "Código SAP": "0918", "Estado": "Activa", "CUIT": "30712188061", "Nombre en AFIP": "GAS Y PETROLEO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA-YPF S.A.-TOTAL AUSTRAL SA SUC ARG-ROVELLA ENERGIA SA-AREA CERRO LAS MINAS UTE",
                -"Nombre Soc SAP": "UTE ZAMPAL OESTE", "Código SAP": "1046", "Estado": "Activa", "CUIT": "30709441945", "Nombre en AFIP": "YPF S.A EQUITABLE RESOURCES ARGENTINA COMPANY S.A - ZAMPAL OESTE UTE",
                -"Nombre Soc SAP": "UTE ENARSA 1", "Código SAP": "1146", "Estado": "Activa", "CUIT": "30710916833", "Nombre en AFIP": "ENERGIA ARGENTINA S.A.- YPF S.A.- PETROBRAS ENERGIA S.A.- PETROURUGUAY S.A. UNION TRANSITORIAS DE EMPRESAS E1",
                -"Nombre Soc SAP": "UTE GNL ESCOBAR", "Código SAP": "1153", "Estado": "Activa", "CUIT": "30711435227", "Nombre en AFIP": "ENERGIA ARGENTINA S.A. - YPF S.A. - PROYECTO GNL ESCOBAR - UNION TRANSITORIA DE EMPRESAS",
                -"Nombre Soc SAP": "UTE RINCON DEL MANGRULLO", "Código SAP": "1160", "Estado": "Activa", "CUIT": "30714428469", "Nombre en AFIP": "YPF S.A - PAMPA ENERGIA S.A.. UNION TRANSITORIA DE EMPRESAS - RINCON DEL MANGRULLO",
                -"Nombre Soc SAP": "UTE CHACHAHUEN", "Código SAP": "1164", "Estado": "Activa", "CUIT": "30716199025", "Nombre en AFIP": "YPF S.A.-KILWER S.A.-KETSAL S.A.-ENERGIA MENDOCINA S.A. AREA CHACHAHUEN UNION TRANSITORIA DE EMPRESAS",
                -"Nombre Soc SAP": "UTE La amarga chica", "Código SAP": "1167", "Estado": "Activa", "CUIT": "30714869759", "Nombre en AFIP": "YPF S.A. - PETRONAS E&P ARGENTINA S.A.",
                -"Nombre Soc SAP": "UTE EL OREJANO", "Código SAP": "1169", "Estado": "Activa", "CUIT": "30715142658", "Nombre en AFIP": "YPF S.A.- PBB POLISUR S.A., AREA EL OREJANO UNION TRANSITORIA",
                -"Nombre Soc SAP": "CIA HIDROCARBURO NO CONVENCIONAL SRL", "Código SAP": "1171", "Estado": "Activa", "CUIT": "30714124427", "Nombre en AFIP": "COMPAÑIA DE HIDROCARBURO NO CONVENCIONAL S.R.L.",
                -"Nombre Soc SAP": "UTE PAMPA (YSUR)", "Código SAP": "1632", "Estado": "Activa", "CUIT": "30711689067", "Nombre en AFIP": "APACHE ENERGIA ARGENTINA S.R.L. - PETROLERA PAMPA S.A., UNION TRANSITORIA DE EMPRESAS - ESTACION FERNANDEZ ORO Y ANTICLINAL CAMPAMENTO"

            **Aclaración sobre lista de sociedades permitidas:**
            - Cada elemento de la lista hace referencia a una unica sociedad.
            - Cada apartado de un elemento sirve para identificar a la misma sociedad. Los apartados estan delimitados por ','.
            - Siempre vas a devolver la sociedad encontrada como se indique en el apartado 'Nombre Soc SAP' de ese elemento.
            **Ejemplo: Si encontras el valor '30715142658' que corresponde al campo 'CUIT' del elemento cuyo campo 'Nombre Soc SAP' es 'UTE EL OREJANO' y entonces devolves el valor 'UTE EL OREJANO'.

            - Para que Customer Name sea "YPF S.A." se tiene que encontrar ese texto literal en el mail o el literal "YPF SA".

            **Salida esperada:**
            - Se espera que los datos de salida sean en formato json.
            - La estructura de los datos debe ser:
                "file_name":str    #Asunto del mail del que extrajiste los datos
                "fields": []    #Array con los datos extraídos del mail
                "missing_fields": []    #Array con los datos no encontrados en el mail. Solo indicar nombre del campo.
                "error": []     #Siempre vacío
            - Se puede tener mas de una consulta en el mismo mail, de ser asi se debe generar una salida para cada una.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    )

    names_and_cuits_prompt = """Eres un asistente especializado en extraer datos del texto de un email.
    **Los datos a extraer son:
    -"VendorTaxId": se refiere al numero de CUIT de quien realiza la consulta o el reclamo en el mail. No siempre esta presente este numero pero cuando lo está es explícito.
    -"CustomerName": se refiere a la sociedad por la que se hace la consulta. Solo se pueden incluir las sociedades permitidas en la lista de sociedades.
    **Lista de sociedades permitidas:
    -"Nombre Soc SAP": "AESA", "Código SAP": "0478", "Estado": "Activa", "CUIT": "30685211890", "Nombre en AFIP": "ASTRA EVANGELISTA SA"
    -"Nombre Soc SAP": "YPF GAS", "Código SAP": "0522", "Estado": "Activa", "CUIT": "33555234649", "Nombre en AFIP": "YPF GAS S.A."
    -"Nombre Soc SAP": "UTE LA VENTANA", "Código SAP": "0571", "Estado": "Activa", "CUIT": "30652671418", "Nombre en AFIP": "YACIMIENTO LA VENTANA YPF SA SINOPEC ARGENTINA EXPLORATION AND PRODUCTION INC UNION TRANSITORIA"
    -"Nombre Soc SAP": "YPF S.A.", "Código SAP": "0620", "Estado": "Activa", "CUIT": "30546689979", "Nombre en AFIP": "YPF SA",
    -"Nombre Soc SAP": "Fundación YPF", "Código SAP": "0789", "Estado": "Activa", "CUIT": "30691548054", "Nombre en AFIP": "FUNDACION YPF",
    -"Nombre Soc SAP": "UTE LLANCANELO", "Código SAP": "0797", "Estado": "Activa", "CUIT": "30707293809", "Nombre en AFIP": "CONTRATO DE UNION TRANSITORIA DE EMPRESAS - AREA LLANCANELO U.T.E.",
    -"Nombre Soc SAP": "OPESSA", "Código SAP": "0680", "Estado": "Activa", "CUIT": "30678774495", "Nombre en AFIP": "OPERADORAS DE ESTACIONES DE SERVICIO SA",
    -"Nombre Soc SAP": "UTE CAMPAMENTO CENTRAL CAÑADON PERDIDO", "Código SAP": "0862", "Estado": "Activa", "CUIT": "33707856349", "Nombre en AFIP": "YPF S A - SIPETROL ARGENTINA S A - UTE CAMPAMENTO CENTRAL - CAÑADON PERDIDO",
    -"Nombre Soc SAP": "UTE BANDURRIA", "Código SAP": "0900", "Estado": "Activa", "CUIT": "30708313587", "Nombre en AFIP": "YPF S.A WINTENSHALL ENERGIA SA - PAN AMERICAN ENERGY LLC AREA BANDURRIA UTE",
    -"Nombre Soc SAP": "Ute Santo Domingo I y II", "Código SAP": "0901", "Estado": "Activa", "CUIT": "30713651504", "Nombre en AFIP": "GAS Y PETROELO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA - YPF S.A. - AREA SANTO DOMINGO I Y II UTE",
    -"Nombre Soc SAP": "UTE CERRO LAS MINAS", "Código SAP": "0918", "Estado": "Activa", "CUIT": "30712188061", "Nombre en AFIP": "GAS Y PETROLEO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA-YPF S.A.-TOTAL AUSTRAL SA SUC ARG-ROVELLA ENERGIA SA-AREA CERRO LAS MINAS UTE",
    -"Nombre Soc SAP": "UTE ZAMPAL OESTE", "Código SAP": "1046", "Estado": "Activa", "CUIT": "30709441945", "Nombre en AFIP": "YPF S.A EQUITABLE RESOURCES ARGENTINA COMPANY S.A - ZAMPAL OESTE UTE",
    -"Nombre Soc SAP": "UTE ENARSA 1", "Código SAP": "1146", "Estado": "Activa", "CUIT": "30710916833", "Nombre en AFIP": "ENERGIA ARGENTINA S.A.- YPF S.A.- PETROBRAS ENERGIA S.A.- PETROURUGUAY S.A. UNION TRANSITORIAS DE EMPRESAS E1",
    -"Nombre Soc SAP": "UTE GNL ESCOBAR", "Código SAP": "1153", "Estado": "Activa", "CUIT": "30711435227", "Nombre en AFIP": "ENERGIA ARGENTINA S.A. - YPF S.A. - PROYECTO GNL ESCOBAR - UNION TRANSITORIA DE EMPRESAS",
    -"Nombre Soc SAP": "UTE RINCON DEL MANGRULLO", "Código SAP": "1160", "Estado": "Activa", "CUIT": "30714428469", "Nombre en AFIP": "YPF S.A - PAMPA ENERGIA S.A.. UNION TRANSITORIA DE EMPRESAS - RINCON DEL MANGRULLO",
    -"Nombre Soc SAP": "UTE CHACHAHUEN", "Código SAP": "1164", "Estado": "Activa", "CUIT": "30716199025", "Nombre en AFIP": "YPF S.A.-KILWER S.A.-KETSAL S.A.-ENERGIA MENDOCINA S.A. AREA CHACHAHUEN UNION TRANSITORIA DE EMPRESAS",
    -"Nombre Soc SAP": "UTE La amarga chica", "Código SAP": "1167", "Estado": "Activa", "CUIT": "30714869759", "Nombre en AFIP": "YPF S.A. - PETRONAS E&P ARGENTINA S.A.",
    -"Nombre Soc SAP": "UTE EL OREJANO", "Código SAP": "1169", "Estado": "Activa", "CUIT": "30715142658", "Nombre en AFIP": "YPF S.A.- PBB POLISUR S.A., AREA EL OREJANO UNION TRANSITORIA",
    -"Nombre Soc SAP": "CIA HIDROCARBURO NO CONVENCIONAL SRL", "Código SAP": "1171", "Estado": "Activa", "CUIT": "30714124427", "Nombre en AFIP": "COMPAÑIA DE HIDROCARBURO NO CONVENCIONAL S.R.L.",
    -"Nombre Soc SAP": "UTE PAMPA (YSUR)", "Código SAP": "1632", "Estado": "Activa", "CUIT": "30711689067", "Nombre en AFIP": "APACHE ENERGIA ARGENTINA S.R.L. - PETROLERA PAMPA S.A., UNION TRANSITORIA DE EMPRESAS - ESTACION FERNANDEZ ORO Y ANTICLINAL CAMPAMENTO"
    **Aclaración sobre lista de sociedades permitidas:**
    - Cada elemento de la lista hace referencia a una unica sociedad.
    - Cada apartado de un elemento sirve para identificar a la misma sociedad. Los apartados estan delimitados por ','.
    - Siempre vas a devolver la sociedad encontrada como se indique en el apartado 'Nombre Soc SAP' de ese elemento.
    **Ejemplo: Si encontras el valor '30715142658' que corresponde al campo 'CUIT' del elemento cuyo campo 'Nombre Soc SAP' es 'UTE EL OREJANO' el dato a devolver como resultado será 'UTE EL OREJANO'.
    
    **Aclaraciones generales:**
    - Que se mencione "YPF-CAP" o "YPF" no es suficiente para que CustomerName sea YPF S.A. y esto es asi porque YPF S.A. es una sociedad dentro de la empresa YPF.
    - YPF SA puede ser considerado como YPF S.A.
    - No siempre esta presente algun dato de la sociedad en el mail, en caso de no encontrarlo devolve un string vacío.
    - No siempre esta presente el VendorTaxId, en caso de no encontrarlo devuelve un string vacío.

     **Salida esperada:**
    - Se espera que devuelvas un json con:
        -"CustomerName": valor del dato pedido.
        -"CustomerTaxId": se obtiene de la lista de sociedades si y solo si se pudo detectar un CustomerName.
        -"VendorTaxId": valor del dato pedido.
    En caso de que suceda que "VendorTaxId" sea igual a "CustomerTaxId", eliminar el dato del "VendorTaxId".
    """

    invoice_id_prompt = """Eres un asistente especializado en extraer el dato "InvoiceId" del texto de un email. 
    "InvoiceId" hace referencia al número de factura por la que se hace la consulta. Algunos ejemplos de como puede llegar a estar mencionada la factura son: documento, comprobante, certificado, FC, FCA, FCE, FEA, FA.
    -El número de factura se compone de dos partes: el "punto de venta" (un número de hasta 4 dígitos) y el "número de comprobante" (un número de 8 dígitos).
    -El "punto de venta" es opcional y puede o no aparecer en el texto. Si aparece, puede venir con ceros a la izquierda (por ejemplo, "0001") o sin ellos (por ejemplo, "1").
    -El "número de comprobante" es siempre obligatorio y tiene máximo 8 dígitos.
    -El número de factura puede aparecer como una combinación del "punto de venta" y "número de comprobante", separados por un delimitador como "A", "B", "C", "E", "M", "T" o "-".
    -Si el "punto de venta" no está presente, solo se debe considerar el "número de comprobante".
    -El numero de factura generalmente se menciona de forma explicita, pero en el caso de no estar de esa forma intenta encontrarlo siguiendo las reglas que lo conforman.
    -El numero de factura no siempre esta presente y si el remitente menciona que el dato esta adjunto muy posiblemente no se encuentre en el texto del mail.
    -Los mails suelen tener un numero de caso del centro de atencion a proveedores que generalmente se menciona como "YPF-CAP", no se debe confundir ese numero con el numero de factura.
    Se espera que solo devuelvas el dato encontrado. En caso de no encontrar un dato que cumpla con lo pedido entonces devolve solo un string vacío. En caso de obtener mas de un numero de factura devolvelos en un array.
    """

"""
Algunos ejemplos de como puede llegar a estar mencionada la factura son: documento, comprobante, certificado, FC, FCA, FCE, FEA, FA, etc.
Aclaraciones:
Notas pedido de devolucion de retenciones: Debe contener el texto "dichas retenciones no se computaron ni se computaran" matchear por similitud. En caso de no contenerlo rechazar la lectura del archivo.
Siempre viene adjunto con el certificado de retenciones, no se hacen extracciones sobre este archivo.
Debe tener firma del proveedor sino rechazar la extracción de datos.

Pedido de OP y o retenciones: Se suele deja el numero de factura, la razon social del proveedor y la sociedad de YPF.

Formato de factura para SAP
0001A00000058
En caso de no tener todos los numeros completar con ceros si se tiene 58
00000058
Se complementa la busqueda con la fecha o la sociedad de YPF.

Se pueden referir a la factura como documento, comprobante, certificado

Algunos ejemplos de como puede llegar a estar mencionada la factura son: documento, comprobante, certificado, FC, FCA, FCE, FEA, FA, etc.

El número de factura se compone de dos partes: el "punto de venta" (un número de hasta 4 dígitos) y el "número de comprobante" (un número de 8 dígitos).
El "punto de venta" es opcional y puede o no aparecer en el texto. Si aparece, puede venir con ceros a la izquierda (por ejemplo, "0001") o sin ellos (por ejemplo, "1").
El "número de comprobante" es siempre obligatorio y tiene 8 dígitos, con o sin ceros a la izquierda.
El número de factura puede aparecer como una combinación del "punto de venta" y "número de comprobante", separados por un delimitador como "A", "B", "C", "E", "M", "T" o "-". Si no aparece el delimitador, simplemente se deben juntar los dos números.
Si el "punto de venta" no está presente, solo se debe considerar el "número de comprobante".
Si el número de factura no se encuentra explícitamente, pero sigue estas reglas, debe ser identificado y devuelto.

- El punto de venta es un numero de 4 digitos, que puede venir completo o sin ceros a la izquierda. Ejemplo el numero "0001" puede venir como "0001", "001", "01" o "1".
    - El numero de comprobante es un numero de 8 digitos, que al igual que el punto de venta puede venir completo o sin ceros a la izquierda.
    - El numero de factura se conforma por estos dos numeros: El "punto de venta" y el "numero de comprobante". Pueden estar como pueden no estar separados por un delimitador como "A", "B", "C", "E", ""M", "T" o "-".
    - El numero de factura generalmente se menciona de forma explicita, pero en el caso de no estar de esa forma intenta encontrarlo siguiendo las reglas que lo conforman.
    - El numero de factura no siempre esta presente y si el remitente menciona que el dato esta adjunto muy posiblemente no se encuentre en el texto del mail.
    - Se espera que devuelvas unicamente el valor del numero de factura. En caso de no encontrarlo devolve un string vacío sin dar explicaciones. En caso de encontrar mas de uno devolver un array con los numeros sin repetidos.
    - En los mails se suele mencionar un numero de caso que no se debe confundir con el numero de factura. El numero de caso se lo menciona como YPF-CAP."""