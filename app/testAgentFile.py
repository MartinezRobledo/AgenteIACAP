import pandas as pd
from categorizar_emails import categorizar_emails  # Importamos la función desde tu archivo principal

# Ruta del archivo Excel
excel_file_path = "D:\\Python\\agents\\app\\Casos.xlsx"

# Leer los datos del Excel
data = pd.read_excel(excel_file_path)

# Verificar que las columnas necesarias existen
required_columns = ["Asunto", "Cuerpo"]
if not all(col in data.columns for col in required_columns):
    raise ValueError(f"El archivo debe contener las columnas: {', '.join(required_columns)}")

# Iterar sobre las filas para procesar cada caso
results = []
for index, row in data.iterrows():
    subject = row["Asunto"]
    body = row["Cuerpo"]

    # Procesar el caso con el agente
    try:
        category = categorizar_emails(subject, body)  # Usar el agente para clasificar
    except Exception as e:
        category = f"Error: {e}"  # Capturar errores si los hay

    # Guardar el resultado en la lista
    results.append(category)

# Agregar los resultados al DataFrame
data["Categoría"] = results

# Guardar el DataFrame actualizado en un nuevo archivo Excel
output_file_path = "D:\\Python\\agents\\app\\Casos_resultados_executor_4o.xlsx"
data.to_excel(output_file_path, index=False)

print(f"Procesamiento completado. Los resultados se han guardado en {output_file_path}.")
