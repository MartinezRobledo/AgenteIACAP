import asyncio
import json
import pandas as pd
from tabulate import tabulate
from src.configs.classes import Input
from src.agents.agentExtractor import extractor

INPUT_FILE = "D:\\Python\\agents\\tests\\Casos categorizados - Extracción - 310125_categorizados.xlsx"
OUTPUT_FILE = "D:\\Python\\agents\\tests\\Casos - Extracción_resultados_310125.xlsx"

async def process_excel():
    # Cargar el archivo Excel
    df = pd.read_excel(INPUT_FILE)
    
    # Verificar que tenga las columnas necesarias
    if not {'Asunto', 'Cuerpo'}.issubset(df.columns):
        raise ValueError("El archivo Excel debe contener las columnas 'Asunto' y 'Cuerpo'")
    
    # Crear listas separadas para cada campo
    customer_names = []
    customer_tax_ids = []
    invoice_ids = []
    vendor_tax_ids = []

    for index, row in df.iterrows():
        input_data = Input(asunto=row['Asunto'], cuerpo=row['Cuerpo'], adjuntos={})
    
        # Invocar el extractor
        result = await extractor.ainvoke(input_data)
        
        # Extraer solo los campos de interés
        extractions = result.get("extractions", [])
        
        # Asegurar que `extractions` es una lista de diccionarios
        if isinstance(extractions, list) and all(isinstance(item, dict) for item in extractions):
            fields = extractions[0].get("fields", {}) if extractions else {}

            customer_names.append(fields.get("customer_name", ""))
            customer_tax_ids.append(fields.get("customer_tax_id", ""))
            invoice_ids.append(fields.get("invoice_id", ""))
            vendor_tax_ids.append(fields.get("vendor_tax_id", ""))
        else:
            customer_names.append("")
            customer_tax_ids.append("")
            invoice_ids.append("")
            vendor_tax_ids.append("")
        
        print(f"""Resultado fila {row}:\n
              "customer_names": {customer_names[-1]}; "customer_tax_ids": {customer_tax_ids[-1]}; "invoice_ids": {invoice_ids[-1]}; "vendor_tax_ids": {vendor_tax_ids[-1]}""")
    
    # Agregar la columna "Customer Name" en la primera columna disponible
    if "Customer Name" not in df.columns:
        df.insert(len(df.columns), "Customer Name", None)
    # Agregar la columna "Customer Tax ID" en la primera columna disponible
    if "Customer Tax ID" not in df.columns:
        df.insert(len(df.columns), "Customer Tax ID", None)
    # Agregar la columna "Invoice ID" en la primera columna disponible
    if "Invoice ID" not in df.columns:
        df.insert(len(df.columns), "Invoice ID", None)
    # Agregar la columna "Vendor Tax ID" en la primera columna disponible
    if "Vendor Tax ID" not in df.columns:
        df.insert(len(df.columns), "Vendor Tax ID", None)
    
    # Agregar las columnas al DataFrame
    df["Customer Name"] = customer_names
    df["Customer Tax ID"] = customer_tax_ids
    df["Invoice ID"] = invoice_ids
    df["Vendor Tax ID"] = vendor_tax_ids
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Resultados guardados en {OUTPUT_FILE}")

async def process_case():
    
        input_data = Input(asunto="""
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
        result = await extractor.ainvoke({"aggregate": [], "text": "", "images": "", "pdfs": "", "others": "", "input_value": input_data})
        
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
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("Salida procesada correctamente.")

if __name__ == "__main__":
    asyncio.run(process_excel())
    # asyncio.run(process_case())
