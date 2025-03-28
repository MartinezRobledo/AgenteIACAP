# Factura contabilizada con fecha de pago
import json
import re
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

# Casos devolución de retenciones
# 1.	Me pasan nota modelo correcta y retenciones
ret_caso_1 = """: Estimado proveedor,
Hemos recibido su pedido de devolución de retenciones mal calculadas, el mismo fue derivado al sector correspondiente para que, en caso de validarlo, dé curso a la devolución.
Número de caso: [numero de caso] 
Proveedor: [Cuenta - Nombre de cuenta;} – [Número de cuenta]
No existe un plazo establecido para la devolución de retenciones, debe consultar en la Extranet 10 días hábiles posteriores a la aceptación de la nota emitida a YPF
Las devoluciones aparecerán en la Extranet como Documentos AK
Si tiene que informar una exención impositiva, nosotros no podemos gestionarlo, eso lo debe informar siempre a ActualizacionFiscal@proveedoresypf.com 
Recuerde hacer el seguimiento de sus facturas y pagos a través de la Extranet de Proveedores.
Cuando necesite actualizar su CBU, recuerde que puede hacerlo a ingresando a la Extranet de Proveedores y efectuarlo allí de forma rápida y segura.
"""

# 2. No me pasan nota modelo ni retenciones
ret_caso_2 = """<p>Estimado proveedor,</p>

    <p>Recordamos que nos debe enviar lo siguiente para que podamos dar curso al pedido de devolución de retenciones:</p>

    <p><strong>Mail a nuestra dirección con asunto:</strong> Pedido de devolución de retenciones - CUIT Razón Social.</p>

    <p>En el mail debe adjuntar lo siguiente:</p>

    <p><strong>1 - Nota solicitando la devolución de retenciones practicadas erróneamente, que contenga la siguiente información:</strong></p>
    <ul>
        <li><strong>Leyenda:</strong> No se computó ni se computará la retención (si omite esta leyenda no se dará curso a la devolución).</li>
        <li><strong>Razón social y CUIT del proveedor.</strong></li>
        <li><strong>Número de Orden de Pago</strong> o, en su defecto, de las facturas afectadas.</li>
        <li><strong>Fecha en que fue realizada la retención.</strong></li>
        <li><strong>Impuesto o tasa correspondiente</strong> a dicha retención (IVA, Ganancias, Ingresos Brutos, SUSS, etc).</li>
        <li><strong>Si la retención es de Ingresos Brutos,</strong> especificar a qué provincia corresponde.</li>
        <li><strong>Razón social de la empresa del grupo YPF</strong> que aplicó la retención.</li>
        <li><strong>Lugar en donde presentó la factura</strong> que dio lugar a la retención erróneamente calculada (si fue por mail, indicar la casilla de correo).</li>
        <li><strong>Firma de un apoderado de la empresa</strong> (firma y sello; si no posee sello, colocar firma y DNI).</li>
    </ul>

    <p><strong>2 - Certificado de la retención practicada</strong> (debe imprimirlo de la Extranet de proveedores, no es obligatorio que sea el original).</p>

    <p>Se adjunta nota modelo como referencia.</p>

    <p><strong>Enviar solo lo solicitado:</strong> nota y retenciones aplicadas, en un mismo PDF con nombre "Pedido de devolución de retenciones".</p>

    <p><strong>De no contar con toda la documentación descripta anteriormente, NO se dará curso al reclamo.</strong></p>

    <p>No existe un plazo establecido para la devolución de retenciones. Debe consultar en la Extranet 10 días hábiles posteriores a la aceptación de la nota emitida a YPF.</p>

    <p>Las devoluciones aparecerán en la Extranet como <strong>Documentos AK</strong>.</p>

    <p>Atentamente,<br>Equipo de Atención a Proveedores</p>
"""

# 3.	Me pasan solo nota modelo correcta
ret_caso_3 = """"""
#Podemos solicitar y volver a reclamar el envio de las retenciones o descargar por nuestros medios a partir de la información que nos proporciona la nota modelo. 

# 4.	me pasan solo retenciones
ret_caso_4 = """Estimado proveedor, 

Recordamos que nos debe enviar lo siguiente para que podamos dar curso al pedido de devolución de retenciones:
Nota solicitando la devolución de retenciones practicadas erróneamente, que contenga la siguiente información:
•	Leyenda: No se computó ni se computará la retención (si omite esta leyenda no se dará curso a la devolución)
•	Razón social y CUIT del proveedor
•	Número de Orden de Pago o, en su defecto, de las facturas afectadas.
•	Fecha en que fue realizada la retención. 
•	Impuesto o tasa correspondiente a dicha retención (IVA, Ganancias, Ingresos Brutos, SUSS, etc)
•	En caso de que la retención sea aplicada por Ingresos Brutos, especificar a qué provincia corresponde la retención.
•	Razón social de la empresa del grupo YPF que aplicó la retención
•	Lugar en donde presentó la factura que dio lugar a la retención erróneamente calculada (si fue por mail indicar la casilla de mail)
•	Firma de algún apoderado de la Empresa (firma y sello, sino posee sello colocar firma y DNI).
Se adjunta nota modelo como referencia.
Enviar junto con las retenciones en un mismo archivo PDF. 
De no contar con toda la documentación descripta anteriormente, NO se dará curso al reclamo.
"""

# 5.	Me pasan nota modelo incorrecta y retenciones
ret_caso_5 = """<p>Estimado proveedor,</p>
    <p>Recordamos los puntos a cumplir para el envío de la nota de pedido de devolución:</p>
    <ul>
        <li><strong>Leyenda:</strong> No se computó ni se computará la retención (si omite esta leyenda no se dará curso a la devolución).</li>
        <li><strong>Razón social y CUIT del proveedor.</strong></li>
        <li><strong>Número de Orden de Pago</strong> o, en su defecto, de las facturas afectadas.</li>
        <li><strong>Fecha en que fue realizada la retención.</strong></li>
        <li><strong>Impuesto o tasa correspondiente</strong> a dicha retención (IVA, Ganancias, Ingresos Brutos, SUSS, etc).</li>
        <li><strong>Si la retención es de Ingresos Brutos,</strong> especificar a qué provincia corresponde.</li>
        <li><strong>Razón social de la empresa del grupo YPF</strong> que aplicó la retención.</li>
        <li><strong>Lugar en donde presentó la factura</strong> que dio lugar a la retención erróneamente calculada (si fue por mail, indicar la casilla de correo).</li>
        <li><strong>Firma de un apoderado de la empresa</strong> (firma y sello; si no posee sello, colocar firma y DNI).</li>
    </ul>
    REPLACE
    <p>Atentamente,<br>Equipo de Atención a Proveedores</p>
"""

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

def responder_mail_retenciones(extraccion_retenciones):
    msg = ""

    notas = [n for n in extraccion_retenciones if n["es_nota_modelo"]]
    notas_completas = [n for n in notas if n["datos_completos"]]
    notas_firmadas = [n for n in notas_completas if n["firmada"]]

    if notas_completas and notas_firmadas: return msg
    if notas:
        notas = [n for n in notas if not n["datos_completos"] or not n["firmada"]]
        archivos = [re.search(r'(?<=/)([^/]+?)(?:-page_\d+)?(?=\.jpg)', n["file_name"]).group() for n in notas]
        if len(archivos) == 1:
            replace = f"<br><p>Por favor, revise el archivo adjunto: {archivos[0]}</p>"
        elif archivos:
            replace = f"<br><p>Por favor, revise los archivos adjuntos: {' ,'.join(archivos)}</p>"
        else:
            replace = ""

        return ret_caso_5.replace("REPLACE", replace)
        
    return ret_caso_2


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
