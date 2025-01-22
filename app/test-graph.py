import asyncio
import pandas as pd
from agentGraph import graph, InputState

# Ruta del archivo Excel
EXCEL_FILE_PATH = "D:\\Python\\agents\\app\\Casos.xlsx"

async def process_row(asunto: str, cuerpo: str, index) -> str:
    """
    Procesa un solo caso utilizando el grafo definido en el código principal.
    """
    input_state = InputState(asunto=asunto, cuerpo=cuerpo)
    # config = {"configurable": {"thread_id": "1"}}
    output = await graph.ainvoke(input_state)
    print(f"Resultado del caso {index+2}: {output}")

async def main():
    # Leer el archivo Excel
    df = pd.read_excel(EXCEL_FILE_PATH)

    # Verificar las columnas requeridas
    if not {"Asunto", "Cuerpo"}.issubset(df.columns):
        print("El archivo Excel debe tener las columnas 'Asunto' y 'Cuerpo'.")
        return

    # Procesar cada fila del DataFrame
    categorias = []
    for index, row in df.iterrows():
        print(f"Procesando fila {index + 2}...")
        try:
            categoria = await process_row(row["Asunto"], row["Cuerpo"], index)
            categorias.append(categoria)
        except Exception as e:
            print(f"Error al procesar fila {index + 2}: {e}")
            categorias.append("Error")

        # Dormir por 15 segundos entre cada iteración
        print("Esperando 15 segundos...")
        await asyncio.sleep(15)

    # Añadir las categorías al DataFrame
    df["Categoria Calculada"] = categorias

    # Guardar los resultados en un nuevo archivo Excel
    output_file_path = EXCEL_FILE_PATH.replace(".xlsx", "_resultados.xlsx")
    df.to_excel(output_file_path, index=False)
    print(f"Resultados guardados en '{output_file_path}'.")

if __name__ == "__main__":
    asyncio.run(main())
