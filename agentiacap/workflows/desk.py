def faltan_datos_requeridos(resume):
    required_fields = ["CUIT", "Sociedad"]
    
    # Verifica si falta algún campo requerido o está vacío
    falta_campo_requerido = any(not resume.get(field) for field in required_fields)

    # Verifica si no hay facturas o si todas las facturas tienen una "Fecha" vacía
    falta_fecha_factura = not resume.get("Factura") or all(not factura.get("Fecha") for factura in resume["Factura"])

    return falta_campo_requerido or falta_fecha_factura

print(faltan_datos_requeridos({
        "CUIT": "30-59053574-1",
        "Sociedad": "0620",
        "Factura": [
            {
                "ID": "FV-58-NPO-10003",
                "Fecha": "20/11/2024"
            }
        ]
    }))