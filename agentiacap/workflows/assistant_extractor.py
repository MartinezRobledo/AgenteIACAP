from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
import asyncio

# Definimos las funciones async para la extracción de datos
async def ExtractSAP(files: list, inputs: list):
    # Simulación de extracción de datos
    return {
        "sistema": "SAP",
        "inputs": inputs,
        "adjuntos": [{"file_name": file} for file in files]
    }

async def ExtractEsker(files: list, inputs: list):
    # Simulación de extracción de datos
    return {
        "sistema": "Esker",
        "inputs": inputs,
        "adjuntos": [{"file_name": file} for file in files]
    }

# Wrappers para que las funciones async sean compatibles con Langchain
def extract_sap_sync(files, inputs):
    return asyncio.run(ExtractSAP(files, inputs))

def extract_esker_sync(files, inputs):
    return asyncio.run(ExtractEsker(files, inputs))

# Definir herramientas para el agente
tools = [
    Tool(
        name="ExtractSAP",
        func=extract_sap_sync,
        description="Extrae datos de los archivos de SAP. Recibe una lista de archivos y una lista de inputs."
    ),
    Tool(
        name="ExtractEsker",
        func=extract_esker_sync,
        description="Extrae datos de los archivos de Esker. Recibe una lista de archivos y una lista de inputs."
    )
]

# Inicializar el agente
llm = ChatOpenAI(model_name="gpt-4", temperature=0)
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Ejemplo de uso
files = ["CAP123Doc.pdf"]
inputs = [{"invoice": "", "date": "02.01.2025"}, {"invoice": "0002A00000013", "date": ""}]
result = agent.run("Extrae datos de SAP para estos archivos e inputs", files=files, inputs=inputs)
print(result)
