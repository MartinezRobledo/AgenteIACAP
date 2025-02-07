from typing_extensions import Annotated, TypedDict

class Mail(TypedDict):
    asunto:Annotated[str, ...]
    cuerpo:Annotated[str, ...]
    adjuntos:Annotated[list, ...]
    categoria:Annotated[str, ...]
    extracciones:Annotated[list, ...]
    tokens:Annotated[int, ...]
    
class Result(TypedDict):
    category:Annotated[str, ...]
    extractions:Annotated[list, ...]
    tokens:Annotated[int, ...]

# Schemas de entrada y salida
class Input(TypedDict):
    asunto:Annotated[str, ...]
    cuerpo:Annotated[str, ...]
    adjuntos:Annotated[list, ...]

class Output(TypedDict):
    result: Annotated[dict, ...]