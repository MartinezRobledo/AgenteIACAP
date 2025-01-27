import os
from tabulate import tabulate  # Para crear tablas legibles en la salida
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
key = os.getenv("AZURE_OPENAI_API_KEY")

# Función para analizar la factura
def analyze_invoice(file_path: str, fields_to_extract: list) -> dict:
    data = {
        "results": [],        # Para guardar los datos extraídos
        "missing_fields": [], # Para guardar los campos no encontrados
        "error": ""           # Para reportar errores, si ocurren
    }

    try:
        # Leer el archivo en modo binario
        with open(file_path, "rb") as file:
            invoice = file.read()

        # Inicializar el cliente de Azure Document Intelligence
        document_intelligence_client = DocumentIntelligenceClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

        # Enviar el documento para análisis
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-invoice", AnalyzeDocumentRequest(bytes_source=invoice)
        )
        invoices = poller.result()

        # Verificar si hay documentos analizados
        if invoices.documents:
            for idx, invoice in enumerate(invoices.documents):
                invoice_data = []

                # Procesar cada campo
                for field in fields_to_extract:
                    field_data = invoice.fields.get(field)
                    if field_data:
                        # Aquí calculamos un valor de Accuracy como un ejemplo
                        # Supongamos que Accuracy = confidence - un pequeño margen (esto es arbitrario)
                        invoice_data.append({
                            "field": field,
                            "value": field_data.content,
                            "confidence": field_data.confidence,
                        })
                    else:
                        # Campo faltante
                        data["missing_fields"].append(field)
                        invoice_data.append({
                            "field": field,
                            "value": "No encontrado",
                            "confidence": 0,
                            "accuracy": 0
                        })

                # Añadir los resultados de esta factura al listado general
                data["results"].append({
                    "invoice_number": idx + 1,
                    "fields": invoice_data
                })
        else:
            data["error"] = "No se encontraron documentos en el archivo."

    except Exception as e:
        data["error"] = str(e)

    return data


if __name__ == "__main__":
    pdf_path = r"D:\\Python\\agents\\app\\Azure document intelligence\\Casos\\_00020_00001224 CARTOCOR 15-11.pdf"
    fields_to_extract = [
        "VendorName",        # Nombre del proveedor
        "CustomerName",      # Nombre del cliente
        "CustomerTaxId",     # ID fiscal del cliente
        "VendorTaxId",       # ID fiscal del proveedor
        "CustomerAddress",   # Dirección del cliente
        "InvoiceId",         # Número de factura
        "InvoiceDate",       # Fecha de factura
        "InvoiceTotal",      # Total de la factura
    ]

    data = analyze_invoice(pdf_path, fields_to_extract)

    if data["error"]:
        print(f"Error: {data['error']}")
    else:
        # Mostrar los resultados en formato tabla
        for invoice in data["results"]:
            print(f"\nResultados para la factura #{invoice['invoice_number']}:\n")
            table_data = [
                [field["field"], field["value"], field["confidence"]]
                for field in invoice["fields"]
            ]
            print(tabulate(table_data, headers=["Campo", "Valor", "Confianza"], tablefmt="grid"))

        # Mostrar campos que faltaron
        if data["missing_fields"]:
            print("\nCampos no encontrados:")
            for field in set(data["missing_fields"]):
                print(f"- {field}")
