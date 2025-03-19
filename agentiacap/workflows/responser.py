# Factura contabilizada con fecha de pago
import json
from agentiacap.llms.llms import llm4o

caso_1 = """Factura contabilizada con fecha de pago:

Si de la factura se tiene número de invoice con una fecha de pago (comp_date), genera el siguiente correo:
Asunto: Estado de facturas - (Sociedad) Cuerpo:

Estimado Proveedor,

Hemos verificado en el sistema y le informamos:
La factura N° (Nro. de Factura) se encuentra contabilizada con Nro. de OP (número de documento de compensación (comp_doc)) abonada en la fecha (fecha de compensación (comp_date)).

Recuerde que puede descargar los comprobantes mediante Extranet de Proveedores.

Muchas gracias por su atención."""

# Factura contabilizada sin OP generada (Fecha de vencimiento no vencida)
caso_2 = """Factura contabilizada sin OP generada (Fecha de vencimiento no vencida):

Si de la factura se tiene numero de invoice, comp_doc, comp_date pero no tiene una orden de pago (purchase_number), y la fecha de vencimiento (due_date) no ha pasado, genera el siguiente correo:
Asunto: Estado de facturas - (Sociedad) Cuerpo:

Estimado Proveedor,

Hemos verificado en el sistema y le informamos:
La factura N° (Nro. de Factura) se encuentra contabilizada y con fecha de vencimiento (fecha de vencimiento). Actualmente no se ha generado una orden de pago. Puede hacer el seguimiento/control de la misma mediante el Portal de Extranet.

Muchas gracias por su atención."""

# Factura contabilizada sin OP generada (Fecha de vencimiento ya vencida)
caso_3 = """Factura contabilizada sin OP generada (Fecha de vencimiento ya vencida):

Si de la factura se tiene número de invoice, pero no tiene una orden de pago generada (purchase_number) y la fecha de vencimiento (due_date) ya pasó, genera el siguiente correo:
Asunto: Facturas contabilizadas vencidas - (Sociedad) Cuerpo:

Estimado Proveedor,

Hemos verificado en el sistema y le informamos:
La factura N° (Nro. de Factura) se encuentra contabilizada y vencida sin Orden de Pago generada.

Como la Factura ya concluyó con el período para la generación de la fecha de pago y no se llegó a generar, procederemos a realizar el reclamo de la Factura Vencida.

Favor de confirmarme su CBU.

Muchas gracias por su atención."""

# Factura contabilizada vencida sin OP generada, esperando confirmación del CBU_ "CASO INCOMPLETO"
caso_4 = """Factura contabilizada vencida sin OP generada, esperando confirmación del CBU:

Si de la factura se tiene numero de invoice y la fecha de vencimiento (due_date) ya pasó, y se espera confirmación del CBU del proveedor, genera el siguiente correo:
Asunto: Facturas contabilizadas vencidas - (Sociedad) Cuerpo:

Estimado Proveedor,

Hemos verificado en el sistema y le informamos:
La(s) factura(s) N° (Nro. de Factura(s)) se encuentra(n) contabilizada(s) y vencida(s) sin Orden de Pago generada.

Para poder continuar con el reclamo de la factura, favor de confirmarme su CBU.

Una vez recibido su CBU, procederemos a realizar el reclamo correspondiente. Agradecemos su colaboración.

Muchas gracias por su atención."""

# Factura sin los datos necesarios para la búsqueda:
caso_5 = """Factura sin los datos necesarios para la búsqueda:

Si no se encuentran los datos necesarios (CUIT, Sociedad, N° de factura), genera el siguiente correo:
Asunto: CAP - Pedido de información al proveedor Cuerpo:

Estimado Proveedor,

Hemos recibido su consulta y para poder procesar su solicitud, necesitamos que nos brinde los siguientes datos:
- CUIT del proveedor
- Sociedad de YPF (mayormente YPF SA)
- N° de la factura

Agradeceremos que nos proporcione esta información para poder proceder con la búsqueda y resolución de su caso.

Muchas gracias por su atención."""


def responder_mail(datos:list):
    prompt = f"""Eres un asistente experimentado y dedicado a responder emails. Tu tarea consiste en analizar una lista de diccionarios con datos de facturas,
    cada diccionario contiene los datos de una factura en particular. Debés agrupar las facturas por caso y generar un mail conjunto que respete el formato de mail de cada caso con todas las facturas involucradas.
    Los datos a analizar son:
    {datos}
    Los casos posibles son:
    -{caso_1}
    -{caso_2}
    -{caso_3}
    Salida esperada:
    -Se espera en formato html.
    
    Instrucciones adicionales:
    - Si hay múltiples facturas para un mismo caso, deben mencionarse todas en el mismo correo y generar un asunto general a los casos involucrados.
    - Para cada factura, debe indicarse su número y su estado (contabilizada, vencida, etc.).
    - Si el caso involucra un reclamo por CBU, debe incluirse en el correo.
    - El formato del correo debe seguir un estilo coherente y adecuado con la información del caso.
"""


    response = llm4o.generate(
        messages=[prompt], 
        response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "response_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "final_answer": {
                        "type": "object",
                        "properties": {
                            "asunto": {"type":"string"},
                            "cuerpo": {"type":"string"}
                        },
                        "required": ["asunto","cuerpo"],
                        "additionalProperties": False
                    }
                },
                "required": ["final_answer"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
    )
    result = json.loads(response.generations[0][0].text.strip())
    return result["final_answer"]

datos = [
{
"invoice": "0002A00000010",
"date": "03.12.2024",
"due_date": "02.01.2025",
"purchase_number": "2000000051",
"op_date": "02.01.2025",
"comp_doc": "2000000051",
"comp_date": "02.01.2025",
"found": True,
"overdue": True
},
{
"invoice": "0002A00000013",
"date": "21.01.2025",
"due_date": "20.02.2025",
"purchase_number": "2000003170",
"op_date": "19.02.2025",
"comp_doc": "2000003170",
"comp_date": "19.02.2025",
"found": True,
"overdue": False
},
{
"invoice": "0002A00000019",
"date": "21.03.2025",
"due_date": "20.04.2025",
"purchase_number": "2000003170",
"op_date": "19.02.2025",
"comp_doc": "2000003170",
"comp_date": "19.02.2025",
"found": True,
"overdue": False
}
]

# result = responder_mail(datos=datos)
