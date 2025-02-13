from typing_extensions import Annotated, TypedDict

### Clases reutilizables ###

class MailSchema(TypedDict):
    asunto:Annotated[str, ...]
    cuerpo:Annotated[str, ...]
    adjuntos:Annotated[list, ...]
    categoria:Annotated[str, ...]
    extracciones:Annotated[list, ...]
    tokens:Annotated[int, ...]
    
class Result(TypedDict):
    category:Annotated[str, ...]
    extractions:Annotated[list, ...]
    tokens:Annotated[int, ...]

# Schemas de entrada y salida
class InputSchema(TypedDict):
    asunto:Annotated[str, ...]
    cuerpo:Annotated[str, ...]
    adjuntos:Annotated[list, ...]

class OutputSchema(TypedDict):
    result: Annotated[dict, ...]

### Variables Globales ###

categories = [
    "Categoría: Alta de usuario, Descripción: Se suele pedir explícitamente en el asunto o en el cuerpo del mail. Sujeto a palabras claves dentro del contexto de la generación o gestión de un nuevo usuario.",
    "Categoría: Error de registración, Descripción: el reclamo siempre es por fechas de vencimiento mal aplicadas. Sujeto al contexto en que el proveedor reclama una mala asignación de la fecha de vencimiento de su factura en el sistema.", 
    "Categoría: Impresión de NC/ND, Descripción: Ahora se llama “Multas”. Sujeto a palabras clave relacionadas con Multas. Sujeto al contexto en que se reclama o consulta por diferencias en el pago . ", 
    "Categoría: Impresión de OP y/o Retenciones, Descripción: Suele ser una solicitud o pedido de ordenes de pago (OP) o retenciones. Suele estar explicito en el asunto o en el cuerpo del mail un mensaje pidiendo retenciones/OP.",
    "Categoría: Pedido devolución retenciones, Descripción: Suele estar explicito en el asunto o cuerpo del mail. Sujeto a palabras clave relacionadas con una devolución o reintegro de una retención. También se suele hacer mención con frecuencia que se envía una nota o se adjunta una nota solicitando a la devolución del monto retenido.",
    "Categoría: Problemas de acceso, Descripción: Sujeto al contexto en que se reclama por no poder acceder a facturar u obtener información de una factura. No se solicita información de una factura solo se reclama el acceso al sistema.", 
    "Categoría: Otras consultas, Descripción: Consultas generales que no encajan en ninguna de las categorías."
    "Categoría: Estado de facturas, Descripción: Consultas sobre estado de facturas, facturas pendientes, facturas vencidas, facturas impagas, facturas no cobradas, facturas rechazadas (o que se haga alguna mención a algún tipo de rechazo) o que puede estar rechazadas (Sujeto a contexto en que se pide motivo del rechazo de una factura), validar el estado de presentación de una factura para saber si se encuentra bien cargada o aún no se efectuó este paso.",
    "Categoría: Estado de cuenta, Descripción: Se consulta y/o informa el estado de la cuenta para conocer deudas o saldos a favor."
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
    "PurchaseOrderNumber",
    "Signed"
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
    {"Nombre Soc SAP": "UTE PAMPA (YSUR)", "Código SAP": "1632", "Estado": "Activa", "CUIT": "30711689067", "Nombre en AFIP": "APACHE ENERGIA ARGENTINA S.R.L. - PETROLERA PAMPA S.A., UNION TRANSITORIA DE EMPRESAS - ESTACION FERNANDEZ ORO Y ANTICLINAL CAMPAMENTO"},
    {"Nombre Soc SAP": "YPF TECNOLOGIA S.A.", "Código SAP": "1600","Estado": "Activa","CUIT":"30713748508","Nombre en AFIP": "YPF TECNOLOGIA S.A."}
]

relevant_categories = [
    "Estado de facturas", 
    "Pedido devolución retenciones", 
    "Impresión de OP y/o Retenciones"
]