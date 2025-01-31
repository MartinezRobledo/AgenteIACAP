import pandas as pd
import asyncio
from src.workflows.main import graph  # Asegúrate de importar correctamente tu flujo
from src.configs.classes import Input

def process_email(asunto, cuerpo):
    """Función que ejecuta el clasificador y obtiene la categoría del mail."""
    input_data = Input(asunto=asunto, cuerpo=cuerpo, adjuntos="")
    result = asyncio.run(graph.ainvoke(input_data))
    print(f"Resultado obtenido: {result}")
    return result["categoria"]

def main():
    # Cargar el archivo Excel
    df = pd.read_excel("D:\\Python\\agents\\tests\\Casos categorizados - Extracción - 3001.xlsx")
    
    # Verificar que las columnas necesarias existen
    if "Asunto" not in df.columns or "Cuerpo" not in df.columns:
        raise ValueError("El archivo debe contener las columnas 'Asunto' y 'Cuerpo'")
    
    # Procesar cada fila y agregar la categoría
    df["Categoría"] = df.apply(lambda row: process_email(row["Asunto"], row["Cuerpo"]), axis=1)
    
    # Guardar el resultado en un nuevo archivo
    df.to_excel("D:\\Python\\agents\\tests\\Casos categorizados - Extracción - 3001_categorizados.xlsx", index=False)
    print("Proceso completado. Archivo guardado'")

if __name__ == "__main__":
    main()
