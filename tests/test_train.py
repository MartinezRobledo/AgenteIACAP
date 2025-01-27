from sentence_transformers import SentenceTransformer, util

# Cargar el modelo entrenado
model_path = "./email_classifier_model"  # Ruta donde se guardó el modelo
model = SentenceTransformer(model_path)

# Descripciones de categorías
categories = [
    "Categoría: Alta de usuario, Descripción: Se suele pedir explícitamente en el asunto o en el cuerpo del mail. Sujeto a palabras claves dentro del contexto de la generación o gestión de un nuevo usuario.",
    "Categoría: Error de registración, Descripción: el reclamo siempre es por fechas de vencimiento mal aplicadas. Sujeto al contexto en que el proveedor reclama una mala asignación de la fecha de vencimiento de su factura en el sistema.",
    "Categoría: Estado de facturas, Descripción: Consultas sobre estado de facturas, facturas pendientes, facturas vencidas, facturas impagas, facturas no cobradas.",
    "Categoría: Facturas rechazadas, Descripción: Se suele aclarar explícitamente en el asunto o en el cuerpo del mail que la factura fue rechazada. Sujeto a contexto en que se pide motivo del rechazo de una factura.",
    "Categoría: Impresión de NC/ND, Descripción: Ahora se llama “Multas”. Sujeto a palabras clave relacionadas con Multas. Sujeto al contexto en que se reclama o consulta por diferencias en el pago.",
    "Categoría: Impresión de OP y/o Retenciones, Descripción: Suele ser una solicitud o pedido de ordenes de pago (OP) o retenciones. Suele estar explicito en el asunto o en el cuerpo del mail un mensaje pidiendo retenciones/OP.",
    "Categoría: Pedido devolución retenciones, Descripción: Suele estar explicito en el asunto o cuerpo del mail. Sujeto a palabras clave relacionadas con una devolución o reintegro de una retención. También se suele hacer mención con frecuencia que se envía una nota o se adjunta una nota solicitando a la devolución del monto retenido.",
    "Categoría: Presentación de facturas, Descripción: Sujeto al contexto en que el proveedor adjunta una factura y aclara el numero de la factura. Puede explicitar que es una presentación en el asunto como puede no hacerlo, pero siempre se va a referir a un mensaje que indica el adjunto de una factura. Esta no es una categoría en la que entren consultas.",
    "Categoría: Problemas de acceso, Descripción: Sujeto al contexto en que se reclama por no poder acceder a facturar u obtener información de una factura. No se solicita información de una factura solo se reclama el acceso al sistema.",
    "Categoría: Salientes YPF, Descripción: No se aclara explícitamente el texto “Salientes YPF”. Está sujeto al contexto en que se pide INFORMAR AL PROVEEDOR de algo.",
    "Categoría: Otras consultas, Descripción: Consultas generales que no encajan en ninguna de las categorías."
]

# Generar embeddings para las descripciones de categorías
category_embeddings = model.encode(categories)

# Función para clasificar un correo
def classify_email(email_text):
    # Generar embedding del correo
    email_embedding = model.encode(email_text)

    # Calcular la similitud coseno con cada categoría
    similarities = util.cos_sim(email_embedding, category_embeddings)

    # Obtener la categoría más similar
    best_match_idx = similarities.argmax().item()
    best_match_category = categories[best_match_idx].split(",")[0].split(":")[1].strip()

    return best_match_category

# Ejemplo de uso
if __name__ == "__main__":
    new_email = """Estimados,

Muchas gracias por su respuesta.
¿Dónde o cómo debo hacer para cambiar el mail de contacto?
La dirección de correo FLORENCIA.MANIFIESTO@GLOBALDATA.COM ya no existe, y debería ser PEDRO.IBANEZ@GLOBALDATA.COM el mail de contacto.

Gracias,
Pedro Ibanez

Respuesta de Facturación YPF

De: Facturación YPF facturacion@proveedoresypf.com
Para: Pedro Ibanez Pedro.Ibanez@globaldata.com
Fecha: 15/01/2025

Estimado proveedor,

Se le informa acerca del estado de la factura 0003A00000063, la cual se encuentra rechazada.

Motivo del rechazo: Factura rechazada en AFIP por error en la fecha de vencimiento del pago consignada en la FCE. Refacturar y enviar al buzón.
Mail donde se informó: FLORENCIA.MANIFIESTO@GLOBALDATA.COM
Fecha de rechazo: 13/06/2024
Saludos,
    """
    predicted_category = classify_email(new_email)
    print(f"Categoría predicha: {predicted_category}")
