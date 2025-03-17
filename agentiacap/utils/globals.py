from typing_extensions import Annotated, TypedDict

### Clases reutilizables ###

class MailSchema(TypedDict):
    cuerpo_original:str
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
    "CustomerCodSap",
    "VendorTaxId",
    "CustomerAddress",
    "InvoiceId",
    "InvoiceDate",
    "InvoiceTotal",
    "PurchaseOrderNumber",
    "Signed"
]

lista_sociedades = [
    {'Nombre Soc SAP': '', 'Código SAP': '', 'Estado': '', 'CUIT': '', 'Nombre en AFIP': ''}, 
    {'Nombre Soc SAP': 'A - EVANGELISTA S.A.', 'Código SAP': '478', 'Estado': 'Activa', 'CUIT': '30685218190', 'Nombre en AFIP': 'A EVANGELISTA S A'}, 
    {'Nombre Soc SAP': 'AESA', 'Código SAP': '478', 'Estado': 'Activa', 'CUIT': '30685218190', 'Nombre en AFIP': 'A EVANGELISTA S A'}, 
    {'Nombre Soc SAP': 'YPF GAS SOCIEDAD ANONIMA', 'Código SAP': '522', 'Estado': 'Activa', 'CUIT': '30515488479', 'Nombre en AFIP': 'YPF GAS SOCIEDAD ANONIMA'}, 
    {'Nombre Soc SAP': 'YACIMIENTO LA VENTANA YPF S.A.', 'Código SAP': '571', 'Estado': 'Activa', 'CUIT': '30652671418', 'Nombre en AFIP': 'YACIMIENTO LA VENTANA YPF SA SINOPEC ARGENTINA EXPLORATION AND PRODUCTION INC UTE'}, 
    {'Nombre Soc SAP': 'YPF SA IATE SA UTE', 'Código SAP': '575', 'Estado': 'Activa', 'CUIT': '30656820477', 'Nombre en AFIP': 'YPF S.A IATE S.A UTE          '}, 
    {'Nombre Soc SAP': 'YPF S.A.', 'Código SAP': '620', 'Estado': 'Activa', 'CUIT': '30546689979', 'Nombre en AFIP': 'YPF SOCIEDAD ANONIMA'},
    {'Nombre Soc SAP': 'OPESSA', 'Código SAP': '680', 'Estado': 'Activa', 'CUIT': '30678774495', 'Nombre en AFIP': 'OPERADORA DE ESTACIONES DE SERVICIO SOCIEDAD ANONIMA'}, 
    {'Nombre Soc SAP': 'ACUER DE OPER CONJUN EL LIMITE', 'Código SAP': '781', 'Estado': 'Activa', 'CUIT': '30687155242', 'Nombre en AFIP': 'ACUERDO DE OPERAC CONJUNTAS EL LIMITE'}, 
    {'Nombre Soc SAP': 'FUNDACION YPF', 'Código SAP': '789', 'Estado': 'Activa', 'CUIT': '30691548054', 'Nombre en AFIP': 'FUNDACION YPF'}, 
    {'Nombre Soc SAP': 'LLANCANELO', 'Código SAP': '797', 'Estado': 'Activa', 'CUIT': '30707293809', 'Nombre en AFIP': 'CONTRATO DE UNION TRANSITORIA DE EMPRESAS - AREA LLANCANELO U.T.E.'}, 
    {'Nombre Soc SAP': 'GAS Y PETROLEO DEL NQ SA CON PART', 'Código SAP': '918', 'Estado': 'Activa', 'CUIT': '30712188061', 'Nombre en AFIP': 'GAS Y PETROLEO DEL NEUQUEN SOCIEDAD ANONIMA CON PARTICIPACION ESTATAL MAYORITARIA-YPF S.A.-TOTAL AUSTRAL SA SUC ARG-ROVELLA ENERGIA SA-AREA CERRO LAS MINAS UTE'}, 
    {'Nombre Soc SAP': 'UTE ZAMPAL OESTE - YPF SA -', 'Código SAP': '1046', 'Estado': 'Activa', 'CUIT': '30709441945', 'Nombre en AFIP': 'YPF S.A EQUITABLE RESOURCES ARGENTINA COMPANY S.A - ZAMPAL OESTE UTE'}, 
    {'Nombre Soc SAP': 'AESA PERU', 'Código SAP': '1143', 'Estado': 'Activa', 'CUIT': 'EXTERIOR', 'Nombre en AFIP': 'AESA PERU'}, 
    {'Nombre Soc SAP': 'ENERGIA ARGENTINA S.A. - YPF S.A. -', 'Código SAP': '1153', 'Estado': 'Activa', 'CUIT': '30711435227', 'Nombre en AFIP': 'ENERGIA ARGENTINA S.A. - YPF S.A. - PROYECTO GNL ESCOBAR - UTE'}, 
    {'Nombre Soc SAP': 'UTE RINCON DEL MANGRULLO', 'Código SAP': '1160', 'Estado': 'Activa', 'CUIT': '30714428469', 'Nombre en AFIP': 'YPF S.A - PAMPA ENERGIA S.A.. UNION TRANSITORIA DE EMPRESAS - RINCON DEL MANGRULLO'}, 
    {'Nombre Soc SAP': 'YPF SA KILWER SA AREA CHACHAHUEN', 'Código SAP': '1164', 'Estado': 'Activa', 'CUIT': '30716199025', 'Nombre en AFIP': 'YPF S.A.-KILWER S.A.-KETSAL S.A.-ENERGIA MENDOCINA S.A. AREA CHACHAHUEN UNION TRANSITORIA DE EMPRESAS'}, 
    {'Nombre Soc SAP': 'YPF S.A. - PETRONAS E&P ARGENTINA S', 'Código SAP': '1167', 'Estado': 'Activa', 'CUIT': '30714869759', 'Nombre en AFIP': 'YPF S.A. - PETRONAS E&P ARGENTINA S.A.'}, 
    {'Nombre Soc SAP': 'YPF S.A.- PBB POLISUR S.A., AREA', 'Código SAP': '1169', 'Estado': 'Activa', 'CUIT': '30715142658', 'Nombre en AFIP': 'YPF S.A.- PBB POLISUR S.A., AREA EL OREJANO UTE'}, 
    {'Nombre Soc SAP': 'COMPANIA DE HIDROCARBURO NO CONVENC', 'Código SAP': '1171', 'Estado': 'Activa', 'CUIT': '30714124427', 'Nombre en AFIP': 'COMPAÑIA DE HIDROCARBURO NO CONVENCIONAL S.R.L.'}, 
    {'Nombre Soc SAP': 'AESA BOLIVIA', 'Código SAP': '1457', 'Estado': 'Activa', 'CUIT': 'EXTERIOR', 'Nombre en AFIP': 'AESA BOLIVIA'}, 
    {'Nombre Soc SAP': 'YPF PESA POSA  AREA RIO NEUQUEN POR', 'Código SAP': '1471', 'Estado': 'Activa', 'CUIT': '30716137119', 'Nombre en AFIP': 'YPF, PESA, POSA - AREA RIO NEUQUEN UTE'}, 
    {'Nombre Soc SAP': 'YPF SA EQUINOR ARGENTINA AS', 'Código SAP': '1474', 'Estado': 'Activa', 'CUIT': '30716788683', 'Nombre en AFIP': 'YPF S.A. - EQUINOR ARGENTINA AS SUCURSAL ARGENTINA- AREA CAN 102 UTE'}, 
    {'Nombre Soc SAP': 'GAS Y PETROLEO DEL NEUQUEN SA.', 'Código SAP': '1477', 'Estado': 'Activa', 'CUIT': '30714224960', 'Nombre en AFIP': 'GAS Y PETROLEO DEL NEUQUEN SOCIEDAD ANONIMA -YPF S.A.-PLUSPETROL S.A AREA LAS TACANAS UTE'}, 
    {'Nombre Soc SAP': 'UTE LOMA CAMPANA', 'Código SAP': '1480', 'Estado': 'Activa', 'CUIT': '30714335614', 'Nombre en AFIP': 'YPF S.A - COMPAÑIA DE HIDROCARBURO NO CONVENCIONAL SRL AREA LOMA CAMPANA UTE'}, 
    {'Nombre Soc SAP': 'EXXON MOBIL EXPLORATION ARGENTINA S', 'Código SAP': '1484', 'Estado': 'Activa', 'CUIT': '30715683152', 'Nombre en AFIP': 'EXXON MOBIL EXPLORATION ARGENTINA SRL YPF SA AREA LOMA DEL MOLLE UTE'}, 
    {'Nombre Soc SAP': 'YPF TECNOLOGIA SA', 'Código SAP': '1600', 'Estado': 'Activa', 'CUIT': '30713748508', 'Nombre en AFIP': 'YPF TECNOLOGIA S.A.'}, 
    {'Nombre Soc SAP': 'COMPAÑIA DE DESARROLLO NO CONVENCIO', 'Código SAP': '1603', 'Estado': 'Activa', 'CUIT': '30714412651', 'Nombre en AFIP': 'COMPA IA DE DESARROLLO NO CONVENCIONAL SRL'}, 
    {'Nombre Soc SAP': 'YPF SA CIA DE DESARROLLO NO CONVENC', 'Código SAP': '1604', 'Estado': 'Activa', 'CUIT': '30714739235', 'Nombre en AFIP': 'YPF S.A- COMPAÑIA DE DESARROLLO NO CONVENCIONAL S.R.L AREA CHIHUIDO DE LA SIERRA NEGRA SUDESTE- NARAMBUENA UNION TRANSITORIA DE EMPRESAS'}, 
    {'Nombre Soc SAP': 'UTE BAJO DEL TORO I S.R.L.', 'Código SAP': '1606', 'Estado': 'Activa', 'CUIT': '30715890751', 'Nombre en AFIP': 'BAJO DEL TORO I S.R.L. - YPF S.A. - AREA BAJO DEL TORO UTE'}, 
    {'Nombre Soc SAP': 'UTE BANDURRIA SUR', 'Código SAP': '1607', 'Estado': 'Activa', 'CUIT': '30715884344', 'Nombre en AFIP': 'YPF S.A. - SPM ARGENTINA S.A. - AREA BANDURRIA SUR UTE'}, 
    {'Nombre Soc SAP': 'OLEODUCTO LOMA CAMPANA LAGO PELLEGR', 'Código SAP': '1610', 'Estado': 'Activa', 'CUIT': '30715995413', 'Nombre en AFIP': 'OLEODUCTO LOMA CAMPANA - LAGO PELLEGRINI SA'}, 
    {'Nombre Soc SAP': 'YPF VENTURES SAU', 'Código SAP': '1613', 'Estado': 'Activa', 'CUIT': '33716225289', 'Nombre en AFIP': 'YPF VENTURES SAU'}, 
    {'Nombre Soc SAP': 'YPF LITIO S.A.U.', 'Código SAP': '1614', 'Estado': 'Activa', 'CUIT': '33717818399', 'Nombre en AFIP': 'YPF LITIO SAU'}, 
    {'Nombre Soc SAP': 'YPF DIGITAL', 'Código SAP': '1615', 'Estado': 'Activa', 'CUIT': '33718163809', 'Nombre en AFIP': 'YPF DIGITAL SAU'}, 
    {'Nombre Soc SAP': 'VMOS S.A.U.', 'Código SAP': '1617', 'Estado': 'Activa', 'CUIT': '30718713354', 'Nombre en AFIP': 'VMOS SAU'}, 
    {'Nombre Soc SAP': 'MOBIL ARGENTINA S.A.', 'Código SAP': '1619', 'Estado': 'Activa', 'CUIT': '30658473499', 'Nombre en AFIP': 'MOBIL ARGENTINA SOCIEDAD ANONIMA'}
]

relevant_categories = [
    "Estado de facturas", 
    "Pedido devolución retenciones", 
    "Impresión de OP y/o Retenciones"
]

prompt_nota_modelo = """
Analiza el siguiente archivo PDF y responde en formato JSON si cumple con las siguientes condiciones:

1. El documento está firmado.
2. Contiene el siguiente texto exacto en algún lugar: "dichas retenciones no se computaron ni se computarán".

Formato de respuesta esperado (sin explicaciones adicionales):

{
  "firmado": true/false,
  "contiene_texto": true/false
}
"""