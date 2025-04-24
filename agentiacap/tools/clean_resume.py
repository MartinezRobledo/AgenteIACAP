import datetime
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
from langchain.schema import HumanMessage
from agentiacap.llms.llms import llm4o


load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),          
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

resume = {
        "CUIT": "20106088986",
        "Proveedor": "CIENTÍFICA NACIONAL",
        "Sociedad": "YPF TECNOLOGIA SA",
        "Cod_Sociedad": "1600",
        "Facturas": [
            {
                "Factura": "5008209040",
                "Fecha": ":29.03.2025",
                "Monto": "1.372,68\nUSD"
            },
            {
                "Factura": "00005304",
                "Fecha": "31/03/2025",
                "Monto": "USD\n1660,94"
            },
            {
                "Factura": "0001-00020694",
                "Fecha": "14-03-2025",
                "Monto": ""
            },
            {
                "Factura": "20-10608898-6",
                "Fecha": "31-03-2025",
                "Monto": ""
            },
            {
                "Factura": "0002-00005304",
                "Fecha": "31-03-2025",
                "Monto": "1660,94"
            },
            {
                "Factura": "A00002-00005304",
                "Fecha": "31-03-2025",
                "Monto": ""
            },
            {
                "Factura": "001-00005304",
                "Fecha": "",
                "Monto": ""
            }
        ]
    }

# Prompt de limpieza de facturas
prompt = f"""
Dado un objeto diccionario con un resumen de facturas de un proveedor quiero que hagas una limpieza de los datos siguiendo los siguientes pasos:

1. **Eliminar duplicados**:
   - Considerá duplicado cualquier registro que tenga la misma combinación de `Fecha` y `Monto`.
   - También considerá como duplicados registros que tengan el mismo número de factura, incluso si varía el formato (ej: `0004A00575102`, `575102`, `A0004-000575102`, etc.). Identificá prefijos o formatos comunes y unificá si es posible.

2. **Normalizar facturas**:
   - Si una factura tiene un formato corto o incompleto, intentá inferir el formato completo combinando partes con otras facturas existentes del mismo proveedor.
   - Las facturas que solo tienen el número sin tipo (`A`, `B`, etc.) o punto de venta pueden ser igualadas con otras si la numeración es coincidente.

3. **Detectar datos inválidos o inventados**:
   - Considerá inválidas las facturas que:
     - Son números de CUIT.
     - Son secuencias artificiales (ej: `1234-56789012`, `1111-11111111`, etc.).
     - No tienen estructura coherente con una factura típica.

4. **Evaluar si falta información**:
   - Agregá un campo booleano `faltante_info` en la raíz del JSON.
   - Este campo será `true` si:
     - No hay ninguna entrada con número de factura.
     - No hay al menos una combinación válida de `Fecha` y `Monto`.
   - Si hay al menos una entrada válida con alguno de esos datos, se considera que **no falta información**.

5. **Generar resultado final**:
   - Mantené el mismo formato JSON original, pero:
     - Eliminá facturas inválidas o duplicadas.
     - Añadí el campo `faltante_info`.
     - Añadí un array llamado `razones_descartes` que detalle para cada entrada descartada: `Factura`, `Fecha`, `Monto`, y el motivo del descarte.

Este es el objeto resume que debes procesar:
{resume}
Devolvé solo el JSON final como respuesta.
"""

response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "invoice_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "CUIT": {"type": "string"},  # CUIT del proveedor
                "Proveedor": {"type": "string"},  # Nombre del proveedor
                "Sociedad": {"type": "string"},  # Nombre de la sociedad
                "Cod_Sociedad": {"type": "string"},  # Código de la sociedad
                "Facturas": {  # Array de facturas
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Factura": {"type": ["string", "null"]},  # Número de factura
                            "Fecha": {"type": ["string", "null"]},  # Fecha de la factura
                            "Monto": {"type": ["string", "null"]},  # Monto de la factura
                            "faltante_info": {"type": "boolean"},  # Flag de información faltante
                            "razones_descartes": {  # Razones de descarte
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "Factura": {"type": "string"},
                                        "Fecha": {"type": "string"},
                                        "Monto": {"type": "string"},
                                        "Razon": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["Factura", "Fecha", "Monto"],  # Campos obligatorios por factura
                        "additionalProperties": False
                    }
                }
            },
            "required": ["CUIT", "Proveedor", "Sociedad", "Cod_Sociedad", "Facturas"],
            "additionalProperties": False
        }
    }
}


# Llamada al modelo con response_format
response = llm4o.invoke(prompt, response_format=response_format)

# Ya es un dict, podés usarlo directamente
print(response)
