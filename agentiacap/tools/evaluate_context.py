import random
import json
from pathlib import Path
from langchain_core.messages import HumanMessage
from langgraph.graph import MessagesState
from agentiacap.llms.llms import llm4o

BASE_DIR = Path(__file__).resolve().parent  # Directorio del script actual
json_file = BASE_DIR / "Ejemplos.json"

# Tools
def evaluar_contexto(categoria: str, email_entrada: str) -> MessagesState:
    """
    Evalúa si un email pertenece a una categoría en base a ejemplos precargados en la tool y devuelve un booleano para indicar la validación.

    Args:
        categoria (str): Categoría a evaluar.
        email_entrada (str): Email que se evaluará.

    Returns:
        bool: Es valido.
    """
    # Obtener 5 casos aleatorios de la categoría
    casos = obtener_casos(categoria, n=5)
    
    # Armar el prompt
    prompt = armar_prompt(categoria, casos, email_entrada)
    
    # Llamar al modelo de Azure OpenAI
    respuesta = llm4o.invoke([HumanMessage(content=prompt)])
    
    return {"messages": [respuesta]}


# Functions
def obtener_casos(categoria, n=5):
    """
    Obtiene un número definido de casos aleatorios de una categoría específica.
    
    Args:
        categoria (str): La categoría a buscar.
        n (int): Número de casos a devolver.

    Returns:
        list: Lista con hasta `n` textos de la categoría solicitada.
    """
    # Cargar el archivo JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrar casos que pertenecen a la categoría solicitada
    casos_filtrados = [item["Datos"] for item in data if item["Categoria"] == categoria]
    
    # Verificar si hay suficientes casos
    if not casos_filtrados:
        raise ValueError(f"No se encontraron casos para la categoría '{categoria}'.")

    # Seleccionar aleatoriamente hasta `n` casos
    return random.sample(casos_filtrados, min(len(casos_filtrados), n))

def armar_prompt(categoria, casos, email):
    """
    Construye un prompt para el modelo de lenguaje.

    Args:
        categoria (str): Categoría del análisis.
        casos (list): Lista de textos de ejemplo.
        texto_entrada (str): Texto que se evaluará.

    Returns:
        str: Prompt para el modelo de lenguaje.
    """
    prompt = f"""Eres un modelo de IA que compara textos de emails para evaluar si comparten el mismo contexto. 
    La categoría que estamos analizando es '{categoria}'. A continuación, te proporciono algunos casos de ejemplo para esta categoría:

    {chr(10).join(f"- {caso}" for caso in casos)}

    Ahora, evalúa si el siguiente email que estamos procesando pertenece a esta categoría basándote en los ejemplos:
    Email entrada: {email}
    Estima el nivel de similitud en un rango del 0 al 100 y contempla un umbral de 80 para aprobar o rechazar la categoría.
    Si supera el umbral aclara en la respuesta 'APROBADA: "Categoría asignada"' donde categoría asignada es la categoría que se generó como respuesta.
    Si es que NO supera el umbral aclara en la respuesta 'RECHAZADA'.
    """
    return prompt