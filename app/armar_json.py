import pandas as pd
import json

def excel_to_json(excel_file, output_json):
    # Leer el archivo Excel
    try:
        df = pd.read_excel(excel_file)

        # Verificar que las columnas necesarias existan
        required_columns = {'Asunto', 'Cuerpo', 'Categoría'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"El archivo Excel debe contener las columnas: {', '.join(required_columns)}")

        # Crear la estructura deseada
        data = []
        for _, row in df.iterrows():
            item = {
                "Datos": f"Asunto: {row['Asunto']} ; Cuerpo: {row['Cuerpo']}",
                "Categoria": row['Categoría']
            }
            data.append(item)

        # Guardar el archivo JSON
        with open(output_json, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        print(f"Archivo JSON creado exitosamente: {output_json}")

    except Exception as e:
        print(f"Error: {e}")

# Ejemplo de uso
excel_file = "D:\\Python\\agents\\app\\Casos categorizados.xlsx" 
output_json = "D:\\Python\\agents\\app\\Casos categorizados.json"  # Nombre del archivo JSON de salida
excel_to_json(excel_file, output_json)
