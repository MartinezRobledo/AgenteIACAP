from fastapi import FastAPI
from src.workflows.main import graph

app = FastAPI()

@app.get("/")
def agent():
    return graph.invoke({"asunto": "CAP", "cuerpo": "Prueba"})

