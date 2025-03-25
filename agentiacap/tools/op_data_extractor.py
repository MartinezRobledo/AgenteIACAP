from asyncio.log import logger
import json
import os
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from agentiacap.tools.document_intelligence import extract_table_layout, split_pdf_in_pages
from typing import List, Dict, Optional

class ComparativaBusqueda(BaseModel):
    original: str = Field(
        description='Campo destinado a contener el valor original de la factura buscada'
    )
    encontrada: str = Field(
        description='Campo destinado a contener el valor completo de la factura encontrada'
    )

class ResultadoBusqueda(BaseModel):
    encontradas: List[ComparativaBusqueda] = Field(
        description='Lista de facturas encontradas en la búsqueda'
    )
    no_encontradas: List[str] = Field(
        description='Lista de facturas no encontradas en la búsqueda'
    )

fields_to_extract_sap = [
    "purchase_number",
    "due_date",
]

fields_to_extract_esker = [
    "date",
    "rejection_reason"
]

def asistente(user_prompt):
    try:
        system_prompt = f"""Eres un asistente especializado en obtener datos de documentos. 
            Los documentos que vas a analizar son PDFs que contienen los datos estructurados como tabla.
            Primero se preprocesa el documento con Document Intelligence Prebuilt-Layout y luego se te pasan las lecturas incluidas en un prompt de usuario para que realices la obtencion de datos."""
        user_content = [{
            "type": "text",
            "text": user_prompt
        }]
        
        openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  # Usamos la API key para autenticación
            api_version="2024-12-01-preview" # Requires the latest API version for structured outputs.
        )
        
        completion = openai_client.beta.chat.completions.parse(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            response_format=ResultadoBusqueda,
            max_tokens=10000,
            temperature=0,
            top_p=0.1,
        )
        extractions = completion.choices[0].message.content
        extractions = json.loads(extractions)
        
    except Exception as e:
        extractions = {"error": str(e)}
    
    return extractions

def buscar_encontrados_fechas(inputs, pendientes):
    """
    Extrae las facturas encontradas en la respuesta del modelo.

    :param response: Lista de diccionarios con los datos extraídos del documento.
    :return: Lista de números de factura encontrados.
    """
    encontrados = []

    for resultado in inputs:
        if "fields" in resultado and resultado["fields"]:
            fecha = resultado["fields"].get("date")
            encontrado = resultado["fields"].get("found")
            if encontrado:
                encontrados.append(resultado)
                # Filtro la lista excluyendo el elemento deseado y me aseguro que pendientes siempre sea menor o igual.
                pendientes = [p for p in pendientes if not p["Fecha"] == fecha]
    
    return {"encontrados":encontrados, "pendientes":pendientes}

async def ExtractSAP(files: list, inputs: list):
    try:
        result = []
                    
        for file in files:
            content = file.get("content", b"")
            pages = split_pdf_in_pages(content)
            encontradas = []
            libro = []
            facturas_pendientes = [factura["ID"] for factura in inputs if factura["ID"]]
            if facturas_pendientes:
                for i, page in enumerate(pages):
                    tables = extract_table_layout(file_bytes=page, header_ref="Referencia")
                    df = tables[0]
                    libro.append(
                        {
                            "page": i,
                            "content": df
                        }
                    )

                    user_prompt = f"""Dada esta lista de facturas,
                    **Lista de facturas:**
                    {df["Referencia"]}

                    Indicame cúales de estos intentos de factura se encuentran en la lista:
                    {facturas_pendientes}

                    **Retorno:**
                        - Las facturas encontradas agrupalas como una lista de diccionarios donde ubicaras las facturas originales con la factura que encontraste.
                        - Las facturas no encontradas agrupalas como una lista."""
                    
                    response = asistente(user_prompt)
                    if response.get("error", []):
                        raise Exception({"nodo": "SAP data extractor", "error": response.get("error")})
                    
                    encontradas_page = response.get("encontradas")
                    if encontradas_page:
                        inputs = [i for i in inputs if i["ID"] not in [e["original"] for e in encontradas_page]]
                        encontradas.append(
                            {
                                "page": i,
                                "faturas": encontradas_page
                            }
                        ) 
                    facturas_pendientes = response.get("no_encontradas")

                    if not facturas_pendientes:
                        break
                
            
        for dato in inputs:
            result.append(
                {
                    "sub-category": "Facturas no encontradas",
                    "fields": dato
                }
            )
        return {"extractions": result}
    except Exception as e:
        logger.error(f"Error en 'ExtractSAP': {str(e)}")
        raise
