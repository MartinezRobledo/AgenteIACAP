class Mail:
    asunto:str
    cuerpo:str
    adjuntos:str
    categoría:str
    def __init__(self, asunto: str, cuerpo: str, adjuntos: str, categoría:str):
        self.asunto = asunto
        self.cuerpo = cuerpo
        self.adjuntos = adjuntos
        self.categoría = categoría

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
class Input:
    asunto:str
    cuerpo:str
    adjuntos:str
    def __init__(self, asunto:str, cuerpo:str, adjuntos:str):
        self.asunto=asunto
        self.cuerpo=cuerpo
        self.adjuntos=adjuntos

class Output:
    categoría:str
    data:dict
    def __init__(self, categoría:str, data:dict):
        self.categoría = categoría
        self.data = data