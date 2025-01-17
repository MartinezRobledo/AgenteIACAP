from fastapi import FastAPI
from agent import react

app = FastAPI()

@app.get("/")
def agent():
    # return graph.invoke({"customer_name": "CAP", "my_var": "Prueba"})
    return react.invoke({"customer_name": "CAP", "my_var": "Prueba"})

