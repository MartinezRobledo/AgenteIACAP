from typing import TypedDict

class Mail(TypedDict):
    asunto:str
    cuerpo:str
    adjuntos:str
    categoria:str
    
    # Getters
    def get_asunto(self) -> str:
        return self.asunto

    def get_cuerpo(self) -> str:
        return self.cuerpo

    def get_adjuntos(self) -> str:
        return self.adjuntos

    # Función para vaciar los adjuntos
    def rechazar_adjuntos(self):
        self.adjuntos = ""

# Schemas de entrada y salida
class Input(TypedDict):
    asunto:str
    cuerpo:str
    adjuntos:list

class Output(TypedDict):
    categoria:str
    data:dict