import asyncio
import pandas as pd
from agentCleaner import graph, State

# Ruta del archivo Excel
EXCEL_FILE_PATH = "D:\\Python\\agents\\app\\Casos.xlsx"

async def process_row(cuerpo: str, index) -> str:
    """
    Procesa un solo caso utilizando el grafo definido en el código principal.
    """
    input_state = State(cuerpo=cuerpo)
    print("Input state", input_state)
    output = await graph.ainvoke(input_state)
    print(f"Resultado del caso {index+2}: {output}")
    return output

async def main():
    # Leer el archivo Excel
    df = pd.read_excel(EXCEL_FILE_PATH)

    # Verificar las columnas requeridas
    if not {"Asunto", "Cuerpo"}.issubset(df.columns):
        print("El archivo Excel debe tener las columnas 'Asunto' y 'Cuerpo'.")
        return

    # Procesar cada fila del DataFrame
    for index, row in df.iterrows():
        print(f"Procesando fila {index + 2}...")
        try:
            # Obtener el resultado del procesamiento del cuerpo
            cuerpo_resultado = await process_row(row["Cuerpo"], index)
            # Actualizar el valor de la columna "Cuerpo" con el resultado procesado
            df.at[index, "Cuerpo"] = cuerpo_resultado
        except Exception as e:
            print(f"Error al procesar fila {index + 2}: {e}")
            # En caso de error, agregar un mensaje de error en la columna "Cuerpo"
            df.at[index, "Cuerpo"] = "Error"

        # Dormir por 5 segundos entre cada iteración
        print("Esperando 5 segundos...")
        await asyncio.sleep(5)

    # Guardar los resultados en un nuevo archivo Excel
    output_file_path = EXCEL_FILE_PATH.replace(".xlsx", "_limpiados.xlsx")
    df.to_excel(output_file_path, index=False)
    print(f"Resultados guardados en '{output_file_path}'.")

if __name__ == "__main__":
    asyncio.run(main())
