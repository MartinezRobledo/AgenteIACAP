from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
from langchain.schema import HumanMessage
from agentiacap.llms.llms import llm4o


load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  # ✅ obligatorio ahora
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),          # ✅ obligatorio ahora
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

response = llm4o([HumanMessage(content="Hola, ¿cómo estás?")])
print(response.content)
