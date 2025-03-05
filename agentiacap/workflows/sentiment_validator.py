import pandas as pd
import asyncio
import os
import json
from agentiacap.llms.llms import llm4o

FILE_PATH = r"C:\\Users\Adrián\\Enta Consulting\\Optimización del CAP - General\\Casos.xlsx"

async def sentiment(subject: str, message: str):
    prompt = [
        {"role": "system", "content": "Eres un asistente de análisis de sentimientos."},
        {"role": "user", "content": f"Analiza el sentimiento del siguiente mensaje:\n\nAsunto: {subject}\nMensaje: {message}\n\nResponde solamente con 'positivo', 'negativo' o 'neutral' sin dar explicaciones ni usar markups."}
    ]

    response = await llm4o.agenerate(
        messages=[prompt], 
        response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "sentiment_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "final_answer": {"type": "string"}
                },
                "required": ["final_answer"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
    )
    # return response.choices[0].message.content
    sentiment = json.loads(response.generations[0][0].text.strip())
    return sentiment["final_answer"]

print(asyncio.run(sentiment(subject="Estado de facturas", message="Solicito estado de facturas")))

# async def process_excel(file_path):
#     df = pd.read_excel(file_path)
    
#     # Buscar la primera columna vacía para colocar "Sentimiento"
#     empty_col_index = df.shape[1]
#     df.insert(empty_col_index, "Sentimiento", "")

#     # Procesar cada fila
#     tasks = [sentiment(row["Asunto"], row["Cuerpo"]) for _, row in df.iterrows()]
#     sentiments = await asyncio.gather(*tasks)

#     # Guardar resultados
#     df["Sentimiento"] = sentiments

#     # Renombrar archivo
#     new_file_path = file_path.replace(".xlsx", " (Prueba sentimiento).xlsx")
#     df.to_excel(new_file_path, index=False)

#     print(f"Archivo guardado en: {new_file_path}")

# # Ejecutar el procesamiento
# asyncio.run(process_excel(FILE_PATH))
