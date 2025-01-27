from langchain_openai import AzureChatOpenAI

llm4o_mini = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",  
    api_version="2024-02-15-preview",
    temperature=0,
    max_tokens=10000,
    timeout=None,
    max_retries=2
)