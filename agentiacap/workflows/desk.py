fechas = [factura["Fecha"] for factura in inputs if factura["Fecha"]]
            if fechas:    
                for page in pages:
                    user_prompt = f"""Extrae los datos de la tabla siguiendo estos pasos:
                    **Flujo principal:
                        - Se deben respetar estrictamente las columnas de las que se leen los datos.
                        - Busca en la columna "Fecha doc." la fecha de cada fecha en la lista de facturas. Si no encontras la fecha retorna.
                        - Si lo encontras obtené el numero de 10 digitos que esta en la misma fila sobre la columna "Doc. comp.", obtené 'due_date' de la columna "Vence El", obtené "comp_date" de la columna "Compens." y obtené "invoice" de la columna "Referencia" sobre la misma fila. Si no encontras el numero retorna en este punto.
                        - Con el número obtenido vas a buscar alguna fila que lo contenga en la columna "Nº doc." y tenga el valor 'OP' en la columna "Clas". Si no encontras ninguna fila que cumpla retorna en este punto.
                        - Si encontras dicha fila entonces devolvé el numero de 10 digitos obtenido como 'op' y el la fecha 'op_date' de la columna "Fecha doc.".
                    **Lista de facturas:**
                    {fechas}
                    **Retorno:
                        - Se debe devolver unicamente los datos que se conocen.
                        - Los datos que no se encontraron se deben indicar como un string vacío.
                        - El campo found es un bool que indica si se encontró o no el numero de 10 digitos correspondiente a purchase_number.
                        - El campo overdue es un bool que indica si la fecha actual es mayor a la fecha de vencimeinto que corresponde al campo due_date.
                        - Retorna los datos pedidos por cada fila que cumpla con las condiciones pedidas."""
                    
                    response = analyze_document_layout(client=client, file_bytes=page, user_prompt=user_prompt)
                    resueltos, inputs = buscar_encontrados_fechas(response, inputs).values()
                    if resueltos: 
                        result += resueltos
                    if len(inputs) == 0:
                        return {"extractions": result}
                    fechas = [factura["Fecha"] for factura in inputs if factura["Fecha"]]
                    if not fechas:
                        break