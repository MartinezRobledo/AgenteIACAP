import asyncio
import base64
import json
import os
import glob
import re
import time
import pandas as pd
from agentiacap.utils.globals import InputSchema
from agentiacap.agents.agentExtractor import extractor
from agentiacap.tools.convert_pdf import pdf_page_to_base64

# INPUT_FILE = "D:\\Python\\agents\\tests\\Casos.xlsx"
INPUT_FILE = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Pruebas - 02-05.xlsx"
OUTPUT_FILE = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Casos - Extracción - Resultados.xlsx"

import json
import re

async def process_excel():
    # Cargar el archivo Excel
    df = pd.read_excel(INPUT_FILE, nrows=10)
    
    # Verificar que tenga las columnas necesarias
    if not {'Asunto', 'Cuerpo', 'IDCaso'}.issubset(df.columns):
        raise ValueError("El archivo Excel debe contener las columnas 'Asunto', 'Cuerpo' e 'IDCaso'")
    
    # Crear listas separadas para cada campo
    results = []
    consumos = []
    times = []

    for index, row in df.iterrows():
        try:
            start_time = time.perf_counter()
            case_id = row['IDCaso']
            adjuntos_path = f"C:\\Users\Adrián\\Enta Consulting\\Optimización del CAP - General\\Adjuntos\\{case_id}"

            adjuntos_list = []
            if os.path.exists(adjuntos_path):
                for file_path in glob.glob(os.path.join(adjuntos_path, '*')):
                    file_extension = os.path.splitext(file_path)[1].lower()

                    if file_extension in ['.png', '.jpg', '.jpeg']:
                        with open(file_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                            adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})
                    else:
                        with open(file_path, "rb") as doc_file:
                            encoded_string = base64.b64encode(doc_file.read()).decode("utf-8")
                            adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})

            input_data = InputSchema(asunto=row['Asunto'], cuerpo=row['Cuerpo'], adjuntos=adjuntos_list)

            # Invocar el extractor
            result = await extractor.ainvoke(input_data)
            result = result.get("extractions", {})
            extractions = result[-1].get("data", {})
            consumo = result[-1].get("meta_data", {})
            consumo = consumo.get("total_tokens", {})
            consumos.append(consumo)
            # Asegurarse de que content esté presente
            content = extractions[-1]
            if content:
                # Verificar si se encuentra el bloque JSON en el contenido
                match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if match:
                    json_string = match.group(1)
                    try:
                        extractions_json = json.loads(json_string)
                        results.append(extractions_json)
                        print(f"Fila {index} procesada correctamente.")
                    except json.JSONDecodeError as e:
                        print(f"Error al decodificar JSON en la fila {index}: {e}")
                        results.append(None)
                else:
                    print(f"No se encontró JSON en el contenido de la fila {index}")
                    print(f"Contenido encontrado en su lugar: ", content)
                    results.append(None)
            else:
                print(f"No se encontró 'content' en el resultado de la fila {index}")
                results.append(None)
            elapsed_time = time.perf_counter() - start_time
            times.append(elapsed_time)
            time.sleep(1)
        except:
            time.sleep(5)
            continue
    

    # Agregar la columna "Extracción" en la primera columna disponible
    if "Extracción" not in df.columns:
        df.insert(len(df.columns), "Extracción", None)

    # Agregar la columna "Tokens" en la primera columna disponible
    if "Tokens" not in df.columns:
        df.insert(len(df.columns), "Tokens", None)
    
    # Agregar la columna "Time" en la primera columna disponible
    if "Time" not in df.columns:
        df.insert(len(df.columns), "Time", None)

    # Agregar las columna al DataFrame
    df["Extracción"] = results
    df["Tokens"] = consumos
    df["Time"] = times
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Resultados guardados en {OUTPUT_FILE}")


async def process_case():
    
        input_data = InputSchema(asunto="""
        RE: Pedido de Dev. Retenciones - 30592665472  TECPETROL S.A. - CAP-515904-G8R7G1 YPF-CAP:0541003983
        """, cuerpo="""
        "Adjunto lo solicitado.

Pagar urgente.

Slds,

 

Walter D. Calzada

Cobranzas

Tecpetrol S.A.

Della Paolera 299, Piso 19 (C1001ADA)
( 4018-5949

 

From: PUB:Facturación YPF <facturacion@proveedoresypf.com>
Sent: jueves, 2 de enero de 2025 17:30
To: CALZADA Walter <walter.calzada@tecpetrol.com>
Subject: Pedido de Dev. Retenciones - 30592665472  TECPETROL
S.A. - CAP-515904-G8R7G1 YPF-CAP:0541003983

 

Attention: This email was sent from someone outside the Company. Do not click
links or open attachments unless you recognize the sender and know the content
is safe.

 



Estimado, 
 

Le informamos lo que nos debe enviar para que podamos dar curso al pedido de
devolución de retenciones que indica como erróneas.

 * Mail a nuestra dirección con asunto: Pedido de devolución de retenciones -
   CUIT Razón Social. 
 * En el mail debe adjuntar lo siguiente:

1 -  Nota solicitando la devolución de retenciones practicadas erróneamente, que
contenga la siguiente información:

·         Leyenda: No se computó ni se computará la retención (si omite esta
leyenda no se dará curso a la devolución)

·         Razón social y CUIT del proveedor

·         Número de Orden de Pago o, en su defecto, de las facturas afectadas.

·         Fecha en que fue realizada la retención. 

·         Impuesto o tasa correspondiente a dicha retención (IVA, Ganancias,
Ingresos Brutos, SUSS, etc)

·         En caso de que la retención sea aplicada por Ingresos Brutos,
especificar a qué provincia corresponde la retención.

·         Razón social de la empresa del grupo YPF que aplicó la retención

·         Lugar en donde presentó la factura que dio lugar a la retención
erróneamente calculada (si fue por mail indicar la casilla de mail)

·         Firma de algún apoderado de la Empresa (firma y sello, sino posee
sello colocar firma y DNI).

2 - Certificado de la retención practicada (debe imprimirla de la Extranet de
proveedores, no es obligatorio que sea el original)

Se adjunta nota modelo como referencia

Enviar solo lo solicitado, nota y retenciones aplicadas, en un mismo PDF con
nombre ""Pedido de devolución de retenciones""

De no contar con toda la documentación descripta anteriormente, NO se dará curso
al reclamo.


No existe un plazo establecido para la devolución de retenciones, debe consultar
en la Extranet 10 días hábiles posteriores a la aceptación de la nota emitida a
YPF

Las devoluciones aparecerán en la Extranet como Documentos AK

 

Saludos.
        """, adjuntos=[])
        
        # Invocar el extractor
        result = await extractor.ainvoke(input_data)
        
        # Extraer solo los campos de interés
        extractions = result.get("extractions", [])

        # Si `extractions` es una lista de strings, convertirla a una lista de diccionarios
        if isinstance(extractions, list) and all(isinstance(item, str) for item in extractions):
            extractions = [json.loads(item) for item in extractions]  # Convertir cada string a JSON

        # Si después de esto sigue siendo una lista de listas, aplanarla
        if len(extractions) == 1 and isinstance(extractions[0], list):
            extractions = extractions[0]

        data = extractions  # Ahora debería ser una lista de diccionarios

        # Extraer la información en formato de tabla
        table_data = []
        for item in data:
            file_name = item.get("file_name", "N/A")  # Evitar KeyError si falta la clave
            for field in item.get("fields", []):  # Iterar sobre la lista de campos
                table_data.append([
                    file_name,
                    field.get("CustomerName", "N/A"),
                    field.get("CustomerTaxId", "N/A"),
                    field.get("InvoiceId", "N/A"),
                    field.get("VendorTaxId", "N/A"),
                    field.get("CAPCase", "N/A")
                ])

        # Definir encabezados
        headers = ["File Name", "Customer Name", "Customer Tax ID", "Invoice ID", "Vendor Tax ID", "CAPCase"]

        # Imprimir en formato tabla
        print("Salida procesada correctamente.")

if __name__ == "__main__":
    asyncio.run(process_excel())
    # asyncio.run(process_case())
