import pandas as pd
from bs4 import BeautifulSoup

# Cargar el archivo Excel
df = pd.read_excel("D:\\Python\\AgentIACAP\\Pruebas -12-03-Resultados2.xlsx")

# Función para limpiar HTML y extraer texto
def limpiar_html(texto):
    if pd.isna(texto):
        return ""  # Manejar valores nulos
    return BeautifulSoup(texto, "html.parser").get_text()

# Aplicar la limpieza a toda la columna
df["Message"] = df["Message"].apply(limpiar_html)

# Guardar el resultado en un nuevo archivo
df.to_excel("D:\\Python\\AgentIACAP\\Pruebas -12-03-Resultados2.xlsx", index=False)
