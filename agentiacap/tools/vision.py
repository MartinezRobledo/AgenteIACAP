from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import pandas as pd
import os

# Cargar variables de entorno
load_dotenv()
endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_KEY")
model_id = os.getenv("AZURE_CUSTOM_MODEL_ID")

# Inicializar cliente
client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# Cargar PDF
ruta_pdf = "C:\\Users\\Adrián\\Downloads\\20106088986-1.pdf"
with open(ruta_pdf, "rb") as f:
    file_bytes = f.read()

# Ejecutar análisis
poller = client.begin_analyze_document(
    model_id=model_id,
    body=file_bytes,
    content_type="application/pdf"
)
result = poller.result()

# Buscar tabla etiquetada como 'Datos_Sap'
tabla = result.documents[0].fields.get("Datos_Sap")
if tabla and tabla.type == "array":
    filas = []
    # Iterar sobre los registros de la tabla
    for fila in tabla.value_array:
        # Extraer cada valor de los campos
        n_doc = fila.value_object.get('N° doc', {}).get('valueString', '')
        clas = fila.value_object.get('Clas', {}).get('valueString', '')
        fecha_doc = fila.value_object.get('Fecha doc', {}).get('valueString', '')
        referencia = fila.value_object.get('Referencia', {}).get('valueString', '')
        fecha_base = fila.value_object.get('Fecha base', {}).get('valueString', '')
        vence_el = fila.value_object.get('Vence el', {}).get('valueString', '')
        impte_mon_extr = fila.value_object.get('Impte.mon.extr', {}).get('valueString', '')
        doc_comp = fila.value_object.get('Doc comp', {}).get('valueString', '')
        compens = fila.value_object.get('Compens', {}).get('valueString', '')
        
        # Agregar la fila extraída al listado de filas
        filas.append({
            'N° doc': n_doc,
            'Clas': clas,
            'Fecha doc': fecha_doc,
            'Referencia': referencia,
            'Fecha base': fecha_base,
            'Vence el': vence_el,
            'Impte.mon.extr': impte_mon_extr,
            'Doc comp': doc_comp,
            'Compens': compens
        })

    # Convertir la lista de filas a un DataFrame
    df = pd.DataFrame(filas)

    # Exportar a un archivo Excel
    df.to_excel("Datos_Sap.xlsx", index=False)
    print("✅ Tabla 'Datos_Sap' exportada como Excel")
else:
    print("❌ No se encontró la tabla 'Datos_Sap' o no es del tipo esperado.")
