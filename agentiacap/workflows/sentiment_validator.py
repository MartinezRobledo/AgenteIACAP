import asyncio
import json
from agentiacap.llms.llms import llm4o

FILE_PATH = r"C:\\Users\Adrián\\Enta Consulting\\Optimización del CAP - General\\Casos.xlsx"

async def sentiment(subject: str, message: str):
    prompt = [
        {"role": "system", "content": "Eres un asistente de análisis de sentimientos."},
        {"role": "user", 
         "content": f"""Analiza el siguiente correo electrónico:
         Asunto: {subject}.
         Mensaje: {message}.
         Considerando los siguientes pasos y aspectos:
         Detección del tono general: Evalúa si el mensaje se expresa de forma respetuosa y profesional, o si se percibe alguna carga emocional negativa (uso de palabras agresivas, tono sarcástico, etc.).
         Identificación de quejas y reclamos: Detecta si el correo contiene expresiones de insatisfacción, quejas o reclamos específicos.
         Presta atención a palabras o frases que indiquen descontento, como 'insatisfecho', 'deficiente', 'inaceptable', etc.
         Detección de reportes reiterados: Verifica si se menciona que la misma situación ha sido reportada en ocasiones previas, lo que puede aumentar la urgencia y la prioridad del caso.
         Análisis de contexto y urgencia: Considera si, además del contenido negativo, el mensaje transmite urgencia o frustración que requiera una acción prioritaria.
         Observa si el correo incluye indicios de necesidad de solución inmediata.
         Consideración de lenguaje formal e informal: Aunque el correo pueda ser formal, identifica si existen matices negativos o sarcasmo que indiquen un sentimiento negativo.
         Asignación de prioridad: Basándote en este análisis integral, clasifica el sentimiento general del correo en una de las siguientes tres categorías: negativo, neutral o positivo."""
        }
    ]

    prompt = [
        {"role": "system", 
         "content": """
            Eres un asistente experto en análisis de impacto de correos electrónicos en un negocio. Se te proporcionará un correo recibido de un cliente, y tu tarea es determinar si su contenido representa un aspecto negativo para el negocio o no.

            Analiza el mensaje teniendo en cuenta los siguientes criterios:

            Frustración o insatisfacción: ¿El cliente expresa molestia, queja o decepción con el servicio o proceso?
            Reclamos o exigencias: ¿El correo solicita una corrección o expresa que algo no ha cumplido sus expectativas?
            Escalamiento del problema: ¿El cliente copió a varias personas para presionar una respuesta?
            Urgencia o insistencia: ¿El cliente da a entender que ha esperado demasiado o que necesita una solución inmediata?
            Tono y lenguaje: Aunque el mensaje sea formal, ¿se detecta un tono de reproche o queja?
            Con base en este análisis, clasifica el correo en una de estas dos categorías:

            Negativo: Si el contenido refleja insatisfacción, molestia o un problema que podría afectar la relación con el cliente o la reputación del negocio.
            No negativo: Si el correo solo contiene una consulta, solicitud estándar o comentario sin signos de molestia o insatisfacción relevante.
        """},
        {"role": "user", 
         "content": f"""Analiza el siguiente correo electrónico:
         Asunto: {subject}.
         Mensaje: {message}.
         Se espera que indiques si es el texto es negativo o no y expliques el por que de la decisión."""
        }
    ]

    response = await llm4o.agenerate(
        messages=[prompt], 
        response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "sentiment_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "final_answer": {"type": "string"}
                },
                "required": ["final_answer"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
    )
    # return response.choices[0].message.content
    sentiment = json.loads(response.generations[0][0].text.strip())
    print(sentiment["final_answer"])

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.run(
        sentiment(
            subject="RE: Maria Alejandra Villa - 27-14188893-0 0002C00000323 - Honorarios Profesionales VMOS", 
            message="Buen día a todas,\n\n \n\nComo me pidieron que les comente como iba el proceso de pago les comento:\n\n \n\nEl pago de mi factura aparece para el 28 de marzo, según me informaron en la\nlínea telefónica de atención a proveedores.\n\n \n\nLa condición de la contratación era pago a 15 días de la fecha de envío de la\nfactura a recepción de facturas, que fue el 26/2. Considerando que el trabajo se\nentregó el 12/2, podrían por favor ver la forma que se adelante el pago?\n\n \n\nTomé el trabajo con la condición de que sistema de pago sería el mismo que el de\nServicios Legales donde como máximo a los dos días de entregado el trabajo ellos\nenvían la factura a recepción. La demora en recibir las instrucciones del\nproceso, cosa que pensé que no me correspondería a mí, y los mails que se\nsiguieron para que supiera cómo enviar la factura demoró mi envío a recepción.\n\n \n\nLes pido que me den una mano con esto por favor. Yo cumplí mi parte en tiempo y\nforma.\n\n \n\nEstoy copiando a facturación proveedores.\n\n \n\nDesde ya muchas gracias.\n\n \n\nMaría Villa\n\nTraductora Pública - Certified Translator\n\n+54 9 1149155852\n\n \n\nDe: Maria A Villa [mailto:mariaavilla@gmail.com]\nEnviado el: Wednesday, February 26, 2025 5:52 PM\nPara: 'recepciondefacturas@ypf.com'\nCC: 'CARP, MONICA SUSANA'; 'COVATTI, JULIETA MELINA'; 'CAPALBO, MARIA\nFLORENCIA'; 'DRAIYE, GABRIELA VERONICA'\nAsunto: Maria Alejandra Villa - 27-14188893-0 0002C00000323 - Honorarios\nProfesionales VMOS\n\n \n\nEnvío factura, Slds.\n\n \n\nMaría Villa\n\nTraductora Pública - Certified Translator\n\n+54 9 1149155852"
        )
    )
    loop.close()
