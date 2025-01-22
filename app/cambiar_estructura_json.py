import json

def transformar_json(input_path, output_path):
    # Leer el archivo JSON de entrada
    with open(input_path, 'r', encoding='utf-8') as f:
        datos_entrada = json.load(f)

    datos_salida = []

    for item in datos_entrada:
        # Separar "Asunto" y "Cuerpo" del campo "Datos"
        if "Datos" in item:
            partes = item["Datos"].split(" ; Cuerpo: ")
            asunto = partes[0].replace("Asunto: ", "").strip()
            cuerpo = partes[1] if len(partes) > 1 else ""
        else:
            asunto, cuerpo = "", ""

        # Crear el nuevo objeto con la estructura deseada
        nuevo_item = {
            "Asunto": asunto,
            "Cuerpo": cuerpo,
            "Categoria": item.get("Categoria", "")
        }
        datos_salida.append(nuevo_item)

    # Escribir el archivo JSON de salida
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(datos_salida, f, ensure_ascii=False, indent=4)

    print(f"Archivo transformado guardado en: {output_path}")

# Ejemplo de uso
input_path = "D:\\Python\\agents\\app\\Casos categorizados.json"  # Ruta del archivo JSON de entrada
output_path = "D:\\Python\\agents\\app\\Casos categorizados-Nueva estructura.json"  # Ruta del archivo JSON de salida
transformar_json(input_path, output_path)
