import asyncio
import pandas as pd
from agentGraph import graph, InputState, OutputState

# Ruta del archivo Excel
EXCEL_FILE_PATH = "D:\\Python\\agents\\app\\Casos.xlsx"

async def process_row(asunto: str, cuerpo: str) -> str:
    """
    Procesa un solo caso utilizando el grafo definido en el código principal.
    """
    input_state = InputState(asunto=asunto, cuerpo=cuerpo)
    config = {"configurable": {"thread_id": "1"}}

    # Ejecutar el grafo con el estado inicial
    async for _ in graph.astream(input_state, config):
        pass

    # Obtener el estado final
    state = graph.get_state(config)  # Devuelve un estado completo (no directamente OutputState)
    output_state = state.metadata["writes"].get("output")  # Extraer el OutputState del estado
    print("OutputState: ", output_state)

    # Verificar si el output es válido
    if isinstance(output_state, dict) and "categoria" in output_state:
        return output_state["categoria"]
    else:
        return "Error: Categoría no encontrada"

async def main():
    # Leer el archivo Excel
    df = pd.read_excel(EXCEL_FILE_PATH)

    # Asegurarse de que las columnas necesarias existan
    if not {"Asunto", "Cuerpo", "Categoria"}.issubset(df.columns):
        print("El archivo Excel debe tener las columnas 'Asunto', 'Cuerpo' y 'Categoria'.")
        return

    # Procesar cada fila del DataFrame
    categorias = []
    for index, row in df.iterrows():
        print(f"Procesando fila {index + 1}...")
        categoria = await process_row(row["Asunto"], row["Cuerpo"])
        categorias.append(categoria)

    # Añadir las categorías al DataFrame
    df["Categoria"] = categorias

    # Guardar los resultados en un nuevo archivo Excel
    output_file_path = EXCEL_FILE_PATH.replace(".xlsx", "_resultados.xlsx")
    df.to_excel(output_file_path, index=False)
    print(f"Resultados guardados en '{output_file_path}'.")

if __name__ == "__main__":
    asyncio.run(main())
