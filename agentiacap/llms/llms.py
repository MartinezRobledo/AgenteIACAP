import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# Cargar variables de entorno desde el archivo .env
load_dotenv()

llm4o_mini = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)

llm4o = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)

# Mostrar todas las variables de entorno cargadas
for key, value in os.environ.items():
    if "AZURE" in key or "OPENAI" in key:  # Filtrar solo las relevantes
        print(f"{key}={value}")