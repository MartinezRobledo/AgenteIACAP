from langchain_openai import AzureChatOpenAI
from langchain.agents import initialize_agent, AgentType, AgentExecutor

from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool

# Función para devolver las categorías posibles
def get_categories(query: str) -> str:
    categories = [
    "Categoría: Alta de usuario, Descripción: Se suele pedir explícitamente en el asunto o en el cuerpo del mail. Sujeto a palabras claves dentro del contexto de la generación o gestión de un nuevo usuario.",
    "Categoría: Error de registración, Descripción: el reclamo siempre es por fechas de vencimiento mal aplicadas. Sujeto al contexto en que el proveedor reclama una mala asignación de la fecha de vencimiento de su factura en el sistema.", 
    "Categoría: Estado de facturas, Descripción: Consultas generales sobre facturas, facturación, estado de facturas, facturas pendientes, facturas vencidas, facturas impagas, facturas no cobradas.",
    "Categoría: Facturas rechazadas, Descripción: Se suele aclarar explícitamente en el asunto o en el cuerpo del mail que la factura fue rechazada. Sujeto a contexto en que se pide motivo del rechazo de una factura.", 
    "Categoría: Impresión de NC/ND, Descripción: Ahora se llama “Multas”. Sujeto a palabras clave relacionadas con Multas. Sujeto al contexto en que se reclama o consulta por diferencias en el pago . ", 
    "Categoría: Impresión de OP y/o Retenciones, Descripción: Suele ser una solicitud o pedido de ordenes de pago (OP) o retenciones. Suele estar explicito en el asunto o en el cuerpo del mail un mensaje pidiendo retenciones/OP.",
    "Categoría: Pedido devolución retenciones, Descripción: Suele estar explicito en el asunto o cuerpo del mail. Sujeto a palabras clave relacionadas con una devolución o reintegro de una retención. También se suele hacer mención con frecuencia que se envía una nota o se adjunta una nota solicitando a la devolución del monto retenido.",
    "Categoría: Presentación de facturas, Descripción: Sujeto al contexto en que el proveedor adjunta una factura y aclara el numero de la factura. Puede explicitar que es una presentación en el asunto como puedo no hacerlo, pero siempre se va a referir a un mensaje que indica el adjunto de una factura.", 
    "Categoría: Problemas de acceso, Descripción: Sujeto al contexto en que se reclama por no poder acceder a facturar u obtener información de una factura. No se solicita información de una factura solo se reclama el acceso al sistema.", 
    "Categoría: Salientes YPF, Descripción: No se aclara explícitamente el texto “Salientes YPF”. Está sujeto al contexto en que alguien pide informar al proveedor de algo."
    ]
    return "\n".join(categories)

# Crear la herramienta que devuelve las categorías
categories_tool = Tool(
    name="categories_tool",
    func=get_categories,
    description="Devuelve las categorías y descripciones posibles de un correo"
)

# Define el modelo de OpenAI (reemplaza con tu configuración correcta)
llm = AzureChatOpenAI(
    # azure_deployment="gpt-4o-mini",
    azure_deployment="gpt-4o",    
    api_version="2024-02-15-preview",
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)

# Función para categorizar el correo
def categorize_email(subject: str, body: str, agent: AgentExecutor):
    # Crear el prompt con el asunto y cuerpo del correo, más las categorías posibles
    prompt = f"""Sos un categorizador de casos que se reciben por mail de un contact center de un equipo de facturación. Vas a recibir el asunto y el cuerpo de un mail y tenés que categorizarlo.
                A continuación te dejo el siguiente mail para que lo categorices,\n
                Asunto: {subject}\n
                Cuerpo: {body}\n 
                La respuesta solo puede ser alguna de las opciones posibles para categorizar un mail.
                Usarás la descripción de la categoría obtenida de la tool "get_categories" para basarte y asignar la categoria correcta.
                Si te parece que no aplica ninguna, respondé con Otras consultas."""

    # Llamar al agente para obtener la categoría
    result = agent.invoke({"input": prompt})

    # El resultado debe contener la categoría predicha por el agente
    return result["output"]

# Crear memoria para el agente
memory = ConversationBufferMemory(memory_key="conversation_history", return_messages=True)

# Crear el agente con memoria
tools = [categories_tool]
agent = initialize_agent(
    tools,
    llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)

def categorizar_emails(subject:str, body:str):
    return categorize_email(subject, body, agent)
