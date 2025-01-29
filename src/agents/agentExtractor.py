import asyncio
import operator
import json
import re
from tabulate import tabulate
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage
from src.services.tools.document_intelligence import process_base64_files, ImageFieldExtractor
from src.utils.armar_json_adjuntos_b64 import generate_json_from_file
from typing import Annotated, Any, List, Dict
from langgraph.graph import StateGraph, START, END
from src.configs.classes import Input
from src.configs.llms import llm4o
from src.configs.Prompt_Template import text_extractor_definition, fields_to_extract

text_extractor = text_extractor_definition | llm4o

class State(TypedDict):
    # La lista `aggregate` acumulará valores
    aggregate: Annotated[list, operator.add]
    text: str   # Almacena asunto y cuerpo del mail
    images: list  # Almacena las imagenes adjuntas
    pdfs: list  # Almacena los pdfs adjuntos
    others: list   # Almacena el resto de adjuntos
    input_value: Input  # Valor recibido desde START

class OutputState(TypedDict):
    extractions:dict

class ClassifyNode:
    def __call__(self, state:State) -> Any:
        # "a" pasa valores distintos a "b" y "c"
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
        pdf_extension = (".pdf")
        images, pdfs, others = [], [], []
        files = state["input_value"]["adjuntos"]
        for file in files:
            file_name = file.get("file_name", "").lower()
            if file_name.endswith(image_extensions):
                images.append(file)
            elif file_name.endswith(pdf_extension):
                pdfs.append(file)
            else:
                others.append(others)

        print("Clasificación completada.")
        return {"images": images, "pdfs": pdfs, "others": others, "text": state["input_value"]["asunto"] + state["input_value"]["cuerpo"]}


class ImageNode:
    async def __call__(self, state: State) -> Any:
        # "b" retorna lo que recibió de "a"
        # extractor = ImageFieldExtractor()
        # result = extractor.extract_fields(base64_images=state["images"], fields_to_extract=fields_to_extract)
        result = process_base64_files(base64_files=state["images"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}



class PdfNode:
    async def __call__(self, state: State) -> Any:
        # "c" retorna lo que recibió de "a"
        result = process_base64_files(base64_files=state["pdfs"], fields_to_extract=fields_to_extract)
        return {"aggregate": [result]}

class TextNode:
    async def __call__(self, state: State) -> Any:
        # "c" retorna lo que recibió de "a"
        prompt = HumanMessage(
            content=f"""**Contenido del correo:**
                    {state["text"]}
                    Devuélveme únicamente el JSON con los datos extraídos, sin explicaciones adicionales.
                    """
        )
        result = await text_extractor.ainvoke({"messages": [prompt]})
        content = result.content.strip("```json").strip("```")  # Limpia los delimitadores
        data = json.loads(content)

        # Separar campos válidos y los que tienen "No encontrado"
        valid_fields = {k: v for k, v in data.items() if v != "No encontrado"}
        missing_fields = {k: v for k, v in data.items() if v == "No encontrado"}

        # Formatear la salida final
        formatted_output = {
            "file_name": "Mail",
            "fields": [valid_fields],
            "missing_fields": [missing_fields] if missing_fields else [],
            "error": ""
        }

        return {"aggregate": [formatted_output]}

def merge_results(state: State) -> OutputState:
    """
    Combina los resultados de imágenes y archivos en un único diccionario de extracciones.
    """
    print("Fusionando resultados...")
    return {"extractions": state["aggregate"]}


# Construcción del grafo
builder = StateGraph(input=State, output=OutputState)

# Nodo a: Clasificar archivos
builder.add_node("brancher", ClassifyNode())
builder.add_edge(START, "brancher")

# Nodo de extracción de texto
builder.add_node("extract from text", TextNode())
builder.add_edge("brancher", "extract from text")

# Nodo b: Procesar imágenes
builder.add_node("extract from images", ImageNode())
builder.add_edge("brancher", "extract from images")

# Nodo c: Procesar archivos
builder.add_node("extract from pdf", PdfNode())
builder.add_edge("brancher", "extract from pdf")

# Nodo d: Fusionar resultados
builder.add_node("merger", merge_results)
builder.add_edge("extract from images", "merger")
builder.add_edge("extract from pdf", "merger")
builder.add_edge("extract from text", "merger")
builder.add_edge("merger", END)

extractor = builder.compile()



async def main():
    input_paths = [
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\- Factura 0003-00111312 -  - CARTOCOR S A .pdf",
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png"
    ]

    # Llama a la función `generate_json_from_pdfs` (debe ser adaptada para ser async si no lo es).
    data_json = generate_json_from_file(input_paths)
    input_data = Input(asunto="""RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167) YPF-CAP:0555000834""", cuerpo="""Estimados, buenos días.

 

Por favor, necesitamos tener respuesta sobre el caso CAP-494106-Z4C4D8,
correspondiente a la factura 14-843 (UTE Amarga Chica), la cual ya se encuentra
vencida y por lo que debe ser cancelada a la brevedad. Desde hace semanas que
estamos esperando respuesta sobre este caso.

 

Aguardamos sus comentarios.

 

Muchas gracias.

 

Saludos.

 

Manuel Morelli – Sr Billing Coordinator.

NABORS INTERNATIONAL ARGENTINA S.R.L

manuel.morelli@nabors.com | www.nabors.com [http://www.nabors.com/]

[cid:image001.png@01DB6759.D38969F0]

 

From: Loza, Tatiana <Tatiana.Loza@nabors.com>
Sent: Thursday, December 26, 2024 9:48 AM
To: Facturación YPF <facturacion@proveedoresypf.com>
Cc: Telmo, Leonardo <Leonardo.Telmo@Nabors.com>; Morelli, Manuel
<Manuel.Morelli@Nabors.com>
Subject: RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834

 

Estimados, buenos días.

 

Por favor, necesitamos tener respuesta sobre el caso CAP-494106-Z4C4D8,
correspondiente a la factura 14-843 (UTE Amarga Chica), la cual ya se encuentra
vencida y por lo que debe ser cancelada a la brevedad. Desde hace semanas que
estamos esperando respuesta sobre este caso.

 

Aguardamos sus comentarios.

 

Muchas gracias.

 

Saludos.

 

 

Tatiana G. Loza – Billing Coordinator  

NABORS INTERNATIONAL ARGENTINA S.R.L

tatiana.loza@nabors.com | www.nabors.com [http://www.nabors.com/]

[cid:image001.png@01DB6759.D38969F0]

 

From: Facturación YPF <facturacion@proveedoresypf.com>
Sent: Monday, December 16, 2024 2:29 PM
To: Loza, Tatiana <Tatiana.Loza@nabors.com>
Subject: [EXT] RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834

 

CAUTION! Email External to Nabors | ¡PRECAUCIÓN! Correo electrónico externo a
Nabors | تنبيه! بريد إلكتروني خارجي إلى نابورز

 

Estimados, buenas tardes

 

Dejamos el reclamo en el caso CAP-494106-Z4C4D8

 

 

 

Saludos,

CENTRO DE ATENCIÓN A PROVEEDORES YPF

 

[cid:image002.png@01DB6759.D38969F0]

Atención telefónica: 0810 122 9681 Opción 1  - Lun a vie de 9 a 18 horas

Extranet: https://portalsap.ypf.com/

Presentación de facturas: recepciondefacturas@ypf.com

 

[cid:image003.png@01DB6759.D38969F0]

 

INFORMACIÓN IMPORTANTE

ESTE BUZÓN NO ES DE RECEPCIÓN DE FACTURAS (por favor no nos ponga en copia en
sus presentaciones) 

-  Buzón de Presentación de facturas: recepciondefacturas@ypf.com (No aplica
para las sociedades del grupo YPF Luz)

-  Extranet de Proveedores: https://portalsap.ypf.com/ (Si su mail no está
registrado,  pida el alta a Facturacion@proveedoresypf.com )

-  Formatos de presentación y más información
en https://proveedores.ypf.com/Pago-a-proveedores-preguntas-frecuentes.html

-  Legajos
impositivos: https://proveedores.ypf.com/certificados-e-informacion-impositiva.html

------------------- Mensaje original -------------------
De: Loza, Tatiana <tatiana.loza@nabors.com>;
Recibido: Mon Dec 16 2024 12:42:59 GMT-0300 (hora estándar de Argentina)
Para: facturacion@proveedoresypf.com facturacion@proveedoresypf.com
<facturacion@proveedoresypf.com>; facturacion@proveedoresypf.com
<facturacion@proveedoresypf.com>; Facturacion <facturacion@proveedoresypf.com>;
CC: Morelli, Manuel <manuel.morelli@nabors.com>; Leonardo Telmo
<leonardo.telmo@nabors.com>;
Asunto: RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834



Estimados, buenas tardes.

 

Por favor, necesitamos tener respuesta sobre el caso CAP-494106-Z4C4D8,
correspondiente a la factura 14-843 (UTE Amarga Chica), la cual ya se encuentra
vencida y por lo que debe ser cancelada a la brevedad.

 

Aguardamos sus comentarios.

 

Muchas gracias.

 

Saludos.

 

 

 

Tatiana G. Loza – Billing Coordinator  

NABORS INTERNATIONAL ARGENTINA S.R.L

tatiana.loza@nabors.com | www.nabors.com [http://www.nabors.com/]

[cid:image001.png@01DB6759.D38969F0]

 

From: Loza, Tatiana
Sent: Wednesday, December 4, 2024 9:17 AM
To: 'Facturación YPF' <facturacion@proveedoresypf.com>
Cc: Morelli, Manuel <Manuel.Morelli@Nabors.com>; Telmo, Leonardo
<Leonardo.Telmo@Nabors.com>
Subject: RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834

 

Estimados, buenos días.

 

Por favor, necesitamos tener respuesta de este caso, la factura en cuestión ya
se encuentra vencido y por lo que debe ser cancelada a la brevedad.

 

Muchas gracias.

 

Saludos.

 

Tatiana G. Loza – Billing Coordinator  

NABORS INTERNATIONAL ARGENTINA S.R.L

tatiana.loza@nabors.com | www.nabors.com [http://www.nabors.com/]

[cid:image001.png@01DB6759.D38969F0]

 

From: Loza, Tatiana
Sent: Tuesday, November 19, 2024 3:07 PM
To: 'Facturación YPF' <facturacion@proveedoresypf.com>
Cc: Morelli, Manuel <Manuel.Morelli@Nabors.com>; Telmo, Leonardo
<Leonardo.Telmo@Nabors.com>
Subject: RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834

 

Estimados, buenas tardes.

 

¿Tendrán novedades respecto del procesamiento de esta factura? La misma ya se
encuentra vencida, por lo que necesitamos su cancelación a la brevedad.

 

Muchas gracias.

 

Saludos.

 

Tatiana G. Loza – Billing Coordinator  

NABORS INTERNATIONAL ARGENTINA S.R.L

tatiana.loza@nabors.com | www.nabors.com [http://www.nabors.com/]

[cid:image001.png@01DB6759.D38969F0]

 

From: Loza, Tatiana Tatiana.Loza@nabors.com
Sent: Friday, November 15, 2024 11:43 AM
To: Facturación YPF facturacion@proveedoresypf.com
Cc: Morelli, Manuel Manuel.Morelli@Nabors.com; Telmo, Leonardo
Leonardo.Telmo@Nabors.com
Subject: RE: Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834

 

Estimados, buenos días.

 

Adjunto el mail de envío de la factura y el estado en AFIP. La factura se
encontraba procesada cuando consulté el 10/10 en Portal SAP (ver print), no
entiendo porque ahora no figura y en AFIP tiene como estado “rechazado”, sumado
a que no recibimos ningún mail de rechazo por parte de YPF.

 

Por otro lado, ya habíamos generado un caso por esta factura, pero no tuvimos
respuesta (CAP-494106-Z4C4D8) 

 

Por favor, les solicitamos procesar a la brevedad. Muchas gracias.

 

[cid:image004.png@01DB6759.D38969F0][cid:image005.png@01DB6759.D38969F0]

 

[cid:image006.png@01DB6759.D38969F0]

 

[cid:image007.png@01DB6759.D38969F0]}

 

Saludos.

 

Tatiana G. Loza – Billing Coordinator  

NABORS INTERNATIONAL ARGENTINA S.R.L

tatiana.loza@nabors.com | www.nabors.com [http://www.nabors.com/]

[cid:image001.png@01DB6759.D38969F0]

 

From: Facturación YPF <facturacion@proveedoresypf.com>
Sent: Friday, November 15, 2024 11:35 AM
To: Loza, Tatiana <Tatiana.Loza@nabors.com>
Subject: [EXT] Respuesta CAP-500660-Q3G6R3  - FC 00014A00000843 (1167)
YPF-CAP:0555000834

 

CAUTION! Email External to Nabors | ¡PRECAUCIÓN! Correo electrónico externo a
Nabors | تنبيه! بريد إلكتروني خارجي إلى نابورز

 

Estimada Tatiana,

 

En referencia a la gestión iniciada bajo el caso Nro CAP-500660-Q3G6R3 le
informamos:

 

La FC 0014A00000843 no figura contabilizada ni rechazada.

 

Para poder gestionar un reclamo solicitando que se le informe el status de sus
documentos no contabilizados (ni rechazados), le pedimos por favor que envíe lo
siguiente:

 

 

-Mail que envió a Recepción de Facturas, éste debe ser el mail tal cual lo
envió, con el PDF de la factura. No se aceptarán documentos en formatos
editables. No se aceptan reenvíos, solo elementos de correo
electrónico adjuntos.

-remitirnos una captura de pantalla de su portal AFIP donde se visualice de
forma clara el ESTADO del documento.

 

 

De no cumplir con lo solicitado, no podemos dar curso al reclamo.
Aclaración: Aconsejamos realizar los reclamos por el estado de sus facturas una
vez transcurridos los 15 días de realizada la presentación de su factura, a fin
de cumplir con los plazos necesarios para la registración.

Solo se dará inicio al reclamo si pasaron 15 días corridos desde la presentación
del documento. 

Se recomienda hacer el seguimiento de sus facturas a través de la Extranet o
AFIP respectivamente. 

 

 

 

 

 

 

De no tener respuesta en las siguientes 48 horas este caso será cancelado,
teniendo que enviar un nuevo correo a nuestro buzón si quiere retomarlo.

 

 

Saludos,

CENTRO DE ATENCIÓN A PROVEEDORES YPF

 

[cid:image002.png@01DB6759.D38969F0]

Atención telefónica: 0810 122 9681 Opción 1  - Lun a vie de 9 a 18 horas

Extranet: https://portalsap.ypf.com/

Presentación de facturas: recepciondefacturas@ypf.com

 

[cid:image003.png@01DB6759.D38969F0]

 

INFORMACIÓN IMPORTANTE

ESTE BUZÓN NO ES DE RECEPCIÓN DE FACTURAS (por favor no nos ponga en copia en
sus presentaciones) 

-  Buzón de Presentación de facturas: recepciondefacturas@ypf.com (No aplica
para las sociedades del grupo YPF Luz)

-  Extranet de Proveedores: https://portalsap.ypf.com/ (Si su mail no está
registrado,  pida el alta a Facturacion@proveedoresypf.com )

-  Formatos de presentación y más información
en https://proveedores.ypf.com/Pago-a-proveedores-preguntas-frecuentes.html

-  Legajos
impositivos: https://proveedores.ypf.com/certificados-e-informacion-impositiva.html

------------------- Mensaje original -------------------
De: Bot maker YPF <botmaker@actionmail.app>;
Recibido: Thu Nov 14 2024 12:57:54 GMT-0300 (hora estándar de Argentina)
Para: facturacion@proveedoresypf.com facturacion@proveedoresypf.com
<facturacion@proveedoresypf.com>; facturacion@proveedoresypf.com
<facturacion@proveedoresypf.com>; Facturacion <facturacion@proveedoresypf.com>;
Asunto: YBOT - Estado de Comprobantes - CUIT 33690244239

Hola, quiero saber el estado de mi/s comprobante/s:
Número/s de comprobante/s: 00014A00000843
Correo electrónico: tatiana.loza@nabors.com
Sociedad del grupo YPF a la que facturaron: UTE La Amarga Chica
Fecha/s de presentación: 07/10/2024

¡Saludos![http://url2118.actionmail.app/wf/open?upn=u001.otyO9U6HbGz0cVEZrQ4I-2FzQBbfSufCjXJvXpbnm7UlvZtMhOszgtjy0Mz4liKDTW4bjmWIDT3b4GtBIU3qCNBKTosBCXqOG-2FPLv15NhOCdzOpAe5G96XNX-2B-2FeHfHAqPl0HV-2BCA9y1vjInaF7aA2Z7PzEE4d6L-2FUX4-2FB5s0zQWfZb957O95XYRws7ae81aXpzcPxCgTib-2Bd-2FWrCCU2-2BpJdwJ6NxnMb8TZiynsVgFMgRU-3D]

AVISO LEGAL: Este mensaje y cualquier archivo anexo al mismo son privados y
confidenciales y está dirigido únicamente a su destinatario. Si usted no es el
destinatario original de este mensaje y por este medio pudo acceder a dicha
información por favor elimine el mismo. La distribución o copia de este mensaje
está estrictamente prohibida. Esta comunicación es sólo para propósitos de
información y no debe ser considerada como propuesta, aceptación, tratativas
contractuales, contrato preliminar ni como una declaración de voluntad oficial
por parte de YPF y/o subsidiarias y/o afiliadas y no genera responsabilidad
precontractual ni contractual alguna por su contenido y/o sus adjuntos. La
transmisión de estos mensajes a través de mensajería corporativa no garantiza
que el correo electrónico sea seguro o libre de error. Por consiguiente, no
manifestamos que esta información sea completa o precisa. Toda información está
sujeta a alterarse sin previo aviso. LEGAL NOTICE: The contents of this message
and any attachments are private and confidential and are intended for the
recipient only. If you are not the intended recipient of this message and
through this message you had access to this information, please delete it. The
distribution or copying of this message is strictly prohibited. This
communication is for information purposes only. It shall not be regarded as a
proposal, acceptance, contract negotiation, preliminary contract or official
statement of will by YPF and/or its subsidiaries and/or affiliates, and shall
not create any precontractual or contractual liability whatsoever with regard to
its contents and/or attachments. Email transmission cannot be guaranteed to be
secure or error-free. Therefore, we do not represent that this information is
complete or accurate. All information is subject to change without prior notice.

*******************************
NABORS EMAIL NOTICE - This transmission may be strictly proprietary and
confidential.  If you are not the intended recipient, reading, disclosing,
copying, distributing or using the contents of this transmission is prohibited.
If you have received this in error, please reply and notify the sender (only)
and delete the message. Unauthorized interception of this e-mail is a violation
of federal criminal law. This communication does not reflect an intention by the
sender or the sender's principal to conduct a transaction or make any agreement
by electronic means. Nothing contained in this message or in any attachment
shall satisfy the requirements for a writing, and nothing contained herein shall
constitute a contract or electronic signature under the Electronic Signatures in
Global and National Commerce Act, any version of the Uniform Electronic
Transactions Act, or any other statute governing electronic transactions.

AVISO LEGAL: Este mensaje y cualquier archivo anexo al mismo son privados y
confidenciales y está dirigido únicamente a su destinatario. Si usted no es el
destinatario original de este mensaje y por este medio pudo acceder a dicha
información por favor elimine el mismo. La distribución o copia de este mensaje
está estrictamente prohibida. Esta comunicación es sólo para propósitos de
información y no debe ser considerada como propuesta, aceptación, tratativas
contractuales, contrato preliminar ni como una declaración de voluntad oficial
por parte de YPF y/o subsidiarias y/o afiliadas y no genera responsabilidad
precontractual ni contractual alguna por su contenido y/o sus adjuntos. La
transmisión de estos mensajes a través de mensajería corporativa no garantiza
que el correo electrónico sea seguro o libre de error. Por consiguiente, no
manifestamos que esta información sea completa o precisa. Toda información está
sujeta a alterarse sin previo aviso. LEGAL NOTICE: The contents of this message
and any attachments are private and confidential and are intended for the
recipient only. If you are not the intended recipient of this message and
through this message you had access to this information, please delete it. The
distribution or copying of this message is strictly prohibited. This
communication is for information purposes only. It shall not be regarded as a
proposal, acceptance, contract negotiation, preliminary contract or official
statement of will by YPF and/or its subsidiaries and/or affiliates, and shall
not create any precontractual or contractual liability whatsoever with regard to
its contents and/or attachments. Email transmission cannot be guaranteed to be
secure or error-free. Therefore, we do not represent that this information is
complete or accurate. All information is subject to change without prior notice.

*******************************
NABORS EMAIL NOTICE - This transmission may be strictly proprietary and
confidential.  If you are not the intended recipient, reading, disclosing,
copying, distributing or using the contents of this transmission is prohibited.
If you have received this in error, please reply and notify the sender (only)
and delete the message. Unauthorized interception of this e-mail is a violation
of federal criminal law. This communication does not reflect an intention by the
sender or the sender's principal to conduct a transaction or make any agreement
by electronic means. Nothing contained in this message or in any attachment
shall satisfy the requirements for a writing, and nothing contained herein shall
constitute a contract or electronic signature under the Electronic Signatures in
Global and National Commerce Act, any version of the Uniform Electronic
Transactions Act, or any other statute governing electronic transactions."
""", adjuntos=data_json)
    # Llama a `extraction_node`, asegurándote de que también sea una función asincrónica.
    result = await extractor.ainvoke({"aggregate": [],"text": "", "images": "", "files": "", "input_value": input_data})

    print("Salida: ", result)

# Ejecuta el evento principal asincrónico
if __name__ == "__main__":
    asyncio.run(main())
