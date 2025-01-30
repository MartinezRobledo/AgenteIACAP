import asyncio
import json
import pandas as pd
from src.configs.classes import Input
from src.agents.agentExtractor import extractor

INPUT_FILE = "D:\\Python\\agents\\tests\\Casos - Extracción.xlsx"
OUTPUT_FILE = "D:\\Python\\agents\\tests\\Casos - Extracción_resultados.xlsx"

async def process_excel():
    # Cargar el archivo Excel
    df = pd.read_excel(INPUT_FILE)
    
    # Verificar que tenga las columnas necesarias
    if not {'Asunto', 'Cuerpo'}.issubset(df.columns):
        raise ValueError("El archivo Excel debe contener las columnas 'Asunto' y 'Cuerpo'")
    
    results = []
    for index, row in df.iterrows():
        input_data = Input(asunto=row['Asunto'], cuerpo=row['Cuerpo'], adjuntos={})
        
        # Invocar el extractor
        result = await extractor.ainvoke({"aggregate": [], "text": "", "images": "", "pdfs": "", "others": "", "input_value": input_data})
        
        # Extraer solo los campos de interés
        extractions = result.get("extractions", [])
        extracted_fields = []
        
        for extraction in extractions:
            if isinstance(extraction, str):  
                extraction = json.loads(extraction)  # Convertimos el string JSON a una lista

            if isinstance(extraction, list):  # Si es una lista, iteramos sobre los elementos
                for item in extraction:
                    field_data = {key: value for field in item.get("fields", []) for key, value in field.items()}
                    extracted_fields.append(json.dumps(field_data))
            else:  # Si no es una lista, tratamos el caso normal
                field_data = {key: value for field in extraction.get("fields", []) for key, value in field.items()}
                extracted_fields.append(json.dumps(field_data))
        
        results.append("; ".join(extracted_fields))
    
    # Agregar la columna "Resultado" en la primera columna disponible
    if "Resultado" not in df.columns:
        df.insert(len(df.columns), "Resultado", None)
    
    df["Resultado"] = results
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Resultados guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(process_excel())
