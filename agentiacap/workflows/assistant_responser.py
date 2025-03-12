import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage

llm = ChatOpenAI(temperature=0, model="gpt-4-turbo")

prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content="Eres un asistente que redacta mails en español formal (variante argentina)."),
    HumanMessage(content="""Genera un mail en tono formal argentino respondiendo sobre el estado de las facturas recibidas.  
Categoría: {categoria}  
Facturas: {facturas}  

Formato de mail esperado:  
- Encabezado cordial  
- Explicación clara del estado de cada factura  
- Cierre amable y disposición a consultas  

**Ejemplo de salida:**  
Asunto: Estado de facturas  
Estimado/a,  
Le informamos el estado de las facturas solicitadas:  
Factura X: [estado y detalles]  
Factura Y: [estado y detalles]  
Quedamos atentos a cualquier consulta.  
Saludos cordiales,  
[Nombre del remitente]""")
])

async def generate_mail(data: dict) -> str:
    response = await llm.apredict(
        prompt_template.format(categoria=data["Categoría"], facturas=json.dumps(data["Facturas"], indent=2))
    )
    return response

# 📌 Ejemplo de uso
import asyncio

input_data = {
    "Categoría": "Estado de facturas",
    "Facturas": [
        {
            "Factura": "0000A00001234",
            "Sistema": "SAP",
            "Encontrada": True,
            "Rechazada": False,
            "Datos": {
                "Fecha de vencimiento": "2025/03/10",
                "Monto": 1500.10,
                "OP": "20000000123",
                "Fecha OP": "2025/03/09",
                "Motivo de rechazo": ""
            }
        },
        {
            "Factura": "0000A00001235",
            "Sistema": "Esker",
            "Encontrada": True,
            "Rechazada": True,
            "Datos": {
                "Fecha de vencimiento": "2025/03/10",
                "Monto": 1500.10,
                "OP": "20000000123",
                "Fecha OP": "2025/03/09",
                "Motivo de rechazo": "Facturado a la sociedad equivocada"
            }
        },
        {
            "Factura": "0000A00001234",
            "Sistema": "",
            "Encontrada": False,
            "Rechazada": False,
            "Datos": {
                "Fecha de vencimiento": None,
                "Monto": None,
                "OP": None,
                "Fecha OP": None,
                "Motivo de rechazo": None
            }
        }
    ]
}

email_text = asyncio.run(generate_mail(input_data))
print(email_text)
