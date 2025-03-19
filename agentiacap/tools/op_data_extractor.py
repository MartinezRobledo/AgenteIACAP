from asyncio.log import logger
from agentiacap.tools.document_intelligence import find_in_binary_files_layout

fields_to_extract_sap = [
    "purchase_number",
    "due_date",
]

fields_to_extract_esker = [
    "date",
    "rejection_reason"
]

async def ExtractSAP(files: list, inputs: list):
    try:
        result = []
        for data in inputs:
            invoice, date = data.get("invoice", ""), data.get("date", "")
            user_text_prompt = f"""Extrae los datos de la tabla siguiendo estos pasos:
            **Aclaración: Solo se debe ejecutar el flujo alternativo si el flujo principal lo solicita explícitamente.
            **Flujo principal (obligatorio):
                - Busca en la columna "Referencia" el numero de factura: {invoice}. Si no encontras la factura intenta el flujo alternativo.
                - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp.", obtene 'due_date' de la columna "Vence El" y obtené "date_comp" de la columna "Compens.". Si no encontras el numero retorna en este punto.
                - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
                - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'purchase_number' y el la fecha 'op_date' de la columna "Fecha doc.".
            **Flujo alternativo (Opcional):
                - Busca en la columna "Fecha doc." la fecha: {date}. Si no encontras la fecha retorna.
                - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp.", obtené 'due_date' de la columna "Vence El" y obtené "comp_date" de la columna "Compens.". Si no encontras el numero retorna en este punto.
                - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
                - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'op' y el la fecha 'op_date' de la columna "Fecha doc.".
            **Retorno:
                - Se debe devolver unicamente los datos que se conocen.
                - Los datos que no se encontraron se deben indicar como un string vacío.
                - El campo found es un bool que indica si se encontró o no el numero de 10 digitos correspondiente a purchase_number.
                - El campo overdue es un bool que indica si la fecha actual es mayor a la fecha de vencimeinto que corresponde al campo due_date."""
            result += find_in_binary_files_layout(binary_files=files, fields_to_extract=fields_to_extract_sap, mothod_prompt=user_text_prompt)
        return {"extractions": result}
    except Exception as e:
        logger.error(f"Error en 'ExtractSAP': {str(e)}")
        raise

async def ExtractEsker(files: list, inputs: list):
    try:
        result = []
        for data in inputs:
            invoice, date = data.get("invoice", ""), data.get("date", "")
            user_text_prompt = f"""Extrae los datos de la tabla siguiendo estos pasos:
            **Aclaración: Solo se debe ejecutar el flujo alternativo si el flujo principal lo solicita explícitamente.
            **Flujo principal (obligatorio):
                - Busca en la columna "Número de factura" el numero de factura: {invoice}. Si no encontras la factura intenta el flujo alternativo.
                - Si lo encontras obtené de la misma fila:
                    -La fecha de factura que esta en la columna "Fecha de factura".
                    -El importe de la columna "Importe".
                    -El motivo de rechazo de la columna "Motivo del rechazo".
            **Flujo alternativo (Opcional):
                - Busca en la columna "Fecha de factura" la fecha: {date}. Si no encontras la fecha retorna.
                - Si lo encontras obtené de la misma fila:
                    -La fecha de factura que esta en la columna "Fecha de factura".
                    -El importe de la columna "Importe".
                    -El motivo de rechazo de la columna "Motivo del rechazo".
            **Retorno:
                - Se debe devolver unicamente los datos que se conocen.
                - Los datos que no se encontraron se deben indicar como un string vacío.
                - El campo found es un bool que indica si se encontró o no el numero de factura/fecha.
                - El campo overdue es un bool que indica si la fecha actual es mayor a la fecha de vencimeinto que corresponde al campo date."""
            result += find_in_binary_files_layout(binary_files=files, fields_to_extract=fields_to_extract_esker, mothod_prompt=user_text_prompt)
        return {"aggregate": result}
    except Exception as e:
        logger.error(f"Error en 'ExtractEsker': {str(e)}")
        raise