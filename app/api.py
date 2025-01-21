from fastapi import FastAPI
from agentGraph import graph

app = FastAPI()

@app.get("/")
def agent():
    return graph.invoke({"asunto": "CAP", "cuerpo": "Prueba"})

