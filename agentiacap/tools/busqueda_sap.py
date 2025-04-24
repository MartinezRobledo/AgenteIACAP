from asyncio.log import logger
import json
import os
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from agentiacap.tools.document_intelligence import extract_table_custom_layout, extract_table_layout, split_pdf_in_pages
from typing import List, Dict, Optional
import pandas as pd
import traceback


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

def asistente(user_prompt, response_format):
    try:
        system_prompt = f"""Eres un asistente especializado en obtener datos de documentos. 
            Los documentos que vas a analizar son data frames que contienen los datos estructurados como tabla."""
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
            response_format=response_format,
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

def extractor_wrapper(extractor_func, page_bytes):
    if extractor_func == extract_table_custom_layout:
        return extractor_func(file_bytes=page_bytes)  # solo requiere file_bytes
    else:
        return extractor_func(file_bytes=page_bytes, header_ref="Referencia")  # el normal necesita el header


def procesar_pagina_y_extraer(page_bytes, index, facturas_pendientes, extractor_func):
    df = extractor_wrapper(extractor_func, page_bytes)
    
    user_prompt = f"""Dada esta lista de facturas,
    **Lista de facturas:**
    {df["referencia"]}

    Indicame cúales de estos de numeros de factura se encuentran en la lista de facturas:
    {facturas_pendientes}
    **Aclaración**: Los números de factura de la lista pueden estar expresados con un formato distinto a los números sobre lo que se hace la búsqueda.
    **Retorno:**
        - Las facturas encontradas agrupalas como una lista de diccionarios donde ubicaras las facturas originales con la factura que encontraste.
        - Las facturas no encontradas agrupalas como una lista."""
    
    response = asistente(user_prompt, ResultadoBusqueda)
    if response.get("error", []):
        raise Exception({"nodo": "SAP data extractor", "error": response.get("error")})

    encontradas_page = response.get("encontradas")
    facturas_no_encontradas = response.get("no_encontradas")

    return {
        "page": index,
        "content": df,
        "encontradas": encontradas_page,
        "no_encontradas": facturas_no_encontradas
    }


async def SAP_buscar_por_factura(file:dict, inputs: list):
    """
    Extrae información relacionada a facturas desde un archivo.

    Esta función toma un archivo PDF (en formato binario) que contiene tablas exportadas desde SAP,
    y busca las facturas proporcionadas en `inputs`. Si encuentra coincFacturaencias, intenta obtener
    detalles como el número de orden de pago (OP), fecha de documento, fecha base y fecha de vencimiento.

    Args:
        file (dict): Un diccionario con la clave "content" que contiene el contenFacturao binario del PDF.
        inputs (list): Una lista de diccionarios, cada uno debe tener una clave "Factura" con el número de factura a buscar.

    Returns:
        dict: Un diccionario con la clave "extractions", que contiene una lista de objetos estructurados
        según subcategorías:
            - "Facturas no encontradas"
            - "Estado de facturas"
            - "OPs no encontradas"
    """
    try:
        cant_paginas_custom = 1
        result = []
        content = file.get("content", b"")
        pages = split_pdf_in_pages(content)
        paginas_custom, pages = pages[:cant_paginas_custom], pages[cant_paginas_custom:]
        encontradas = []
        libro = []
        facturas_pendientes = [factura["Factura"] for factura in inputs if factura["Factura"]]
        if facturas_pendientes:
            try:
                # Procesar primeras x paginas con extractor custom
                for i, page in enumerate(paginas_custom):
                    if not facturas_pendientes:
                        break
                    procesado = procesar_pagina_y_extraer(
                        page_bytes=page,
                        index=i,
                        facturas_pendientes=facturas_pendientes,
                        extractor_func=extract_table_custom_layout
                    )
                    libro.append(procesado)
                    if procesado["encontradas"]:
                        inputs = [i for i in inputs if i["Factura"] not in [e["original"] for e in procesado["encontradas"]]]
                        encontradas.append(procesado["encontradas"])
                    facturas_pendientes = procesado["no_encontradas"]

                # Procesar el resto con extractor normal
                for i, page in enumerate(pages):
                    if not facturas_pendientes:
                        break

                    procesado = procesar_pagina_y_extraer(
                        page_bytes=page,
                        index=i + len(paginas_custom),
                        facturas_pendientes=facturas_pendientes,
                        extractor_func=extract_table_layout
                    )
                    libro.append(procesado)
                    if procesado["encontradas"]:
                        inputs = [i for i in inputs if i["Factura"] not in [e["original"] for e in procesado["encontradas"]]]
                        encontradas.append(procesado["encontradas"])
                    facturas_pendientes = procesado["no_encontradas"]

                    if not facturas_pendientes:
                        break
            except Exception as e:
                logger.error(f"Error en 'ExtractSAP' al procesar la página '{i}': {str(e)}")
                raise
                
            
        for dato in inputs:
            result.append(
                {
                    "sub-category": "Facturas no encontradas",
                    "fields": dato
                }
            )

        # Búsqueda de OP y fechas
        facturas_sin_op = []

        for nro_factura in sum(encontradas, []):  # Flatten
            encontrada = nro_factura.get("encontrada")
            original = nro_factura.get("original")
            datos_factura = None
            datos_op = None
            encontrada_en_libro = False

            # Primero buscar en las páginas ya recorrFacturaas
            for pagina_libro in libro:
                df = pagina_libro["content"]
                if "referencia" not in df.columns:
                    continue

                fila_factura = df[df["referencia"] == encontrada]
                if not fila_factura.empty:
                    encontrada_en_libro = True
                    fila = fila_factura.iloc[0]
                    compens = fila.get("doc_comp", "")
                    vence_el = fila.get("vence_el", "")
                    fecha_base = fila.get("fecha_base", "")
                    fecha_compens = fila.get("compens", "")

                    # Buscar la OP en el mismo dataframe
                    fila_op = df[(df["n_doc"] == compens) & (df["clas"] == "OP")]
                    fecha_doc = fila_op["fecha_doc"].iloc[0] if not fila_op.empty else ""

                    if not fecha_doc:
                        continue  # Intentaremos buscar en otras páginas

                    datos_factura = {
                        "OP": compens,
                        "Fecha doc": fecha_doc,
                        "Factura": encontrada,
                        "Fecha base": fecha_base,
                        "Vence el": vence_el,
                        "Fecha compens": fecha_compens,
                    }

                    result.append({
                        "sub-category": "Estado de facturas",
                        "fields": {
                            "original": original,
                            "detalles": datos_factura
                        }
                    })
                    break

            # Si no se encontró OP en páginas recorrFacturaas, buscar en otras
            if encontrada_en_libro and not datos_factura:
                for pagina_libro in libro:
                    df = pagina_libro["content"]
                    fila_factura = df[df["referencia"] == encontrada]
                    if not fila_factura.empty:
                        fila = fila_factura.iloc[0]
                        compens = fila.get("compens", "")

                        fila_op = df[(df["n_doc"] == compens) & (df["clas"] == "OP")]
                        if not fila_op.empty:
                            fecha_doc = fila_op["fecha_doc"].iloc[0]

                            datos_factura = {
                                "OP": compens,
                                "Fecha doc": fecha_doc,
                                "Factura": encontrada,
                                "Fecha base": fila.get("fecha_base", ""),
                                "Vence el": fila.get("vence_el", ""),
                                "Fecha compens": fila.get("fecha_compens", "")
                            }

                            result.append({
                                "sub-category": "Estado de facturas",
                                "fields": {
                                    "original": original,
                                    "detalles": datos_factura
                                }
                            })
                            break

            # Si después de todo no se encontró la OP
            if not datos_factura:
                facturas_sin_op.append({
                    "Factura": encontrada,
                    "original": original
                })

        if facturas_sin_op:
            result.append({
                "sub-category": "OPs no encontradas",
                "fields": facturas_sin_op
            })


        return {"extractions": result}
    except Exception as e:
        logger.error(f"Error en 'ExtractSAP': {str(e)}")
        raise


async def SAP_buscar_por_fecha_monto(file:dict, inputs: list):
    """
    Busca órdenes de pago (OP) y facturas asociadas en un archivo a partir de pares de fecha y monto.

    Esta función toma un archivo PDF (en formato binario) que contiene tablas exportadas desde SAP, 
    y busca coincFacturaencias en la tabla de compensaciones que tengan la misma fecha y monto que los proporcionados 
    por el usuario. Si encuentra coincFacturaencias con una OP, intenta recuperar las facturas asociadas a esa OP.

    Args:
        file (dict): Un diccionario con la clave "content" que contiene el contenFacturao binario del PDF.
        inputs (list): Una lista de diccionarios, cada uno con claves "Fecha" (string) y "Monto" (string).

    Returns:
        dict: Un diccionario con la clave "extractions", que contiene una lista de resultados clasificados en:
            - "Impresion de OP y/o Retenciones": OPs con facturas asociadas.
            - "Facturas no encontradas": OPs encontradas sin facturas asociadas.
            - "OPs no encontradas": Cuando no se encuentra ninguna OP con la fecha y monto proporcionados.
    """
    try:
        todas_las_tablas = []
        ops_encontradas = []
        facturas_encontradas = []

        # Formateo IA para una sola petición
        format_response = {
            "type": "json_schema",
            "json_schema": {
                "name": "fecha_monto",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "pares": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "fecha": {"type": "string"},
                                    "monto": {"type": "string"}
                                },
                                "required": ["fecha", "monto"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["pares"],
                    "additionalProperties": False
                }
            }
        }


        prompt = "Formatea los siguientes pares de fecha y monto:\n"
        for i, item in enumerate(inputs):
            prompt += f"{i+1}. Fecha: {item.get('Fecha')} => dd.MM.yyyy, Monto: {item.get('Monto')} => miles con '.' y decimales con ','\n"

        formato_response = asistente(prompt, format_response)

        if formato_response.get("error"):
            raise Exception(formato_response.get("error"))

        # Obtenés los pares formateados de la propiedad "pares"
        pendientes_formateados = formato_response["pares"]


        content = file.get("content", b"")
        pages = split_pdf_in_pages(content)

        for page in pages:
            tablas = extract_table_layout(page, header_ref="Referencia")
            if not tablas:
                continue

            for tabla in tablas:
                df = tabla.copy()
                df.columns = df.columns.str.lower()
                todas_las_tablas.append(df)

                # Revisar cada par pendiente
                nuevos_pendientes = []
                for par in pendientes_formateados:
                    coincFacturaencias = df[(df["compens"] == par["fecha"]) &
                                        (df["impte_mon_extr"] == par["monto"]) &
                                        (df["clas"] == "OP")]

                    if not coincFacturaencias.empty:
                        for _, fila in coincFacturaencias.iterrows():
                            op = fila.get("n_doc")
                            if op:
                                ops_encontradas.append({"OP":op, "input":par})
                    else:
                        nuevos_pendientes.append(par)  # Sigue pendiente

                pendientes_formateados = nuevos_pendientes

                if not pendientes_formateados:
                    break  # Ya encontramos todas las OP necesarias

            if not pendientes_formateados:
                break

        if not ops_encontradas:
            return {"extractions": [{
                "sub-category": "OPs no encontradas",
                "fields": inputs
            }]}

        # Buscar facturas asociadas a las OPs encontradas
        for item in ops_encontradas:
            op = item.get("OP")
            dato_input = item.get("input")
            detalles = []
            for tabla in todas_las_tablas:  # saltar si no es válFacturaa
                df = tabla.copy()
                df.columns = df.columns.str.lower()

                facturas = df[df["doc_comp"] == op]
                for _, fila in facturas.iterrows():
                    if fila.get("referencia"):
                        detalles.append(
                            {
                                "Factura": fila.get("referencia"),
                                "Fecha base": fila.get("fecha_base"),
                                "Vence el": fila.get("vence_el"),
                                "Monto factura": fila.get("impte_mon_extr")
                            }
                        )
            if detalles:
                facturas_encontradas.append({
                    "sub-category": "Impresion de OP y/o Retenciones",
                    "Input": dato_input,
                    "OP": op,
                    "Detalles": detalles
                })
            else:
                facturas_encontradas.append({
                    "sub-category": "Facturas no encontradas",
                    "Input": dato_input,
                    "OP": op
                })

        return {"extractions": facturas_encontradas}

    except Exception as e:
        logger.error(f"Error en 'Extraccion_SAP_impresion_op': {str(e)}")
        raise

async def SAP_buscar_por_fecha_base(file:dict, inputs: list):
    """
    Busca facturas y órdenes de pago (OP) en un archivo a partir de una fecha.

    Esta función recibe un archivo PDF (en binario) exportado desde SAP y una lista de fechas.
    Para cada fecha base proporcionada, intenta encontrar la factura asociada y luego la OP correspondiente. 
    Si encuentra la factura pero no la OP, lo indica como "OP no encontrada".

    Args:
        file (dict): Un diccionario con la clave "content" que contiene el contenFacturao binario del PDF.
        inputs (list): Una lista de diccionarios con la clave "Fecha" (string).

    Returns:
        dict: Un diccionario con la clave "extractions", que contiene una lista de resultados con subcategorías:
            - "Estado de facturas": cuando se encuentra tanto la factura como la OP.
            - "OPs no encontradas": cuando se encuentra la factura, pero no la OP correspondiente.
    """
    try:
        print("Buscando OP por fecha base...")
        result = []
        libro = []

        # Formateo IA para una sola petición
        format_response = {
            "type": "json_schema",
            "json_schema": {
                "name": "fecha_monto",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "fechas": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "fecha": {"type": "string"},
                                },
                                "required": ["fecha"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["fechas"],
                    "additionalProperties": False
                }
            }
        }


        prompt = "Formatea las siguientes fechas:\n"
        for i, item in enumerate(inputs):
            prompt += f"{i+1}. Fecha: {item.get('Fecha')} => dd.MM.yyyy\n"

        formato_response = asistente(prompt, format_response)

        if formato_response.get("error"):
            raise Exception(formato_response.get("error"))

        fechas_a_buscar = [f["fecha"] for f in formato_response["fechas"]]

        content = file.get("content", b"")
        cant_paginas_custom = 1
        pages = split_pdf_in_pages(content)
        paginas_custom, pages = pages[:cant_paginas_custom], pages[cant_paginas_custom:]
        for page in pages:
            tables = extract_table_layout(file_bytes=page, header_ref="Referencia")
            if not tables:
                continue

            df = tables[0]  # Siempre tenemos una sola tabla por página
            df.columns = df.columns.str.lower()
            df.reset_index(drop=True, inplace=True)
        
            if df.columns.duplicated().any():
                df = df.loc[:, ~df.columns.duplicated()] 
            libro.append(df)

        df_total = pd.concat(libro, ignore_index=True)

        # Una vez levantadas todas las tablas busco coincFacturaencias por fecha base
        fechas_no_encontradas = []
        for fecha in fechas_a_buscar:
            filas_match = df_total[df_total["fecha_base"] == fecha]
            if filas_match.empty:
                fechas_no_encontradas.append(fecha)
                continue

            for _, fila in filas_match.iterrows():
                referencia = fila.get("referencia", "")
                if not referencia:
                    fechas_no_encontradas.append(fecha)
                    continue

                fila_factura = df_total[df_total["referencia"] == referencia]

                if fila_factura.empty:
                    continue

                compens = fila_factura["doc_comp"].iloc[0]
                vence_el = fila_factura["vence_el"].iloc[0]
                fecha_compens = fila_factura["compens"].iloc[0]

                fila_op = df_total[(df_total["n_doc"] == compens) & (df_total["clas"] == "OP")]
                if not fila_op.empty:
                    fecha_doc = fila_op["fecha_doc"].iloc[0]
                    result.append({
                        "sub-category": "Estado de facturas",
                        "fields": {
                            "Fecha base": fecha,
                            "Factura": referencia,
                            "OP": compens,
                            "Fecha doc": fecha_doc,
                            "Vence el": vence_el,
                            "Fecha compens": fecha_compens
                        }
                    })
                else:
                    result.append({
                        "sub-category": "OPs no encontradas",
                        "fields": {
                            "Fecha base": fecha,
                            "Factura": referencia,
                            "OP": "",
                            "Fecha doc": "",
                            "Vence el": vence_el,
                            "Fecha compens": fecha_compens
                        }
                    })

        return {"extractions": result}

    except Exception as e:
        error_info = traceback.format_exc()
        logger.error(f"Error en 'SAP_buscar_por_fecha_base': {str(e)}\n{error_info}")
        raise


async def procesar_solicitud_busqueda_sap(file, inputs):
    grupo_por_factura = []
    grupo_por_fecha_monto = []
    grupo_por_fecha_base = []

    for item in inputs:
        factura = item.get("Factura", "").strip()
        fecha = item.get("Fecha", "").strip()
        monto = item.get("Monto", "").strip()

        if factura:
            grupo_por_factura.append(item)
        elif fecha and monto:
            grupo_por_fecha_monto.append(item)
        elif fecha:
            grupo_por_fecha_base.append(item)

    resultados = []

    if grupo_por_fecha_monto:
        res = await SAP_buscar_por_fecha_monto(file, grupo_por_fecha_monto)
        resultados.extend(res["extractions"])

    if grupo_por_fecha_base:
        res = await SAP_buscar_por_fecha_base(file, grupo_por_fecha_base)
        resultados.extend(res["extractions"])

    if grupo_por_factura:
        res = await SAP_buscar_por_factura(file, grupo_por_factura)
        resultados.extend(res["extractions"])

    return resultados
