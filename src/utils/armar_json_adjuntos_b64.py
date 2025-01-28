import os
import base64

def file_to_base64(file):
    """
    Convierte un archivo PDF a base64.
    :param file_path: Ruta al archivo PDF.
    :return: El contenido del archivo en formato base64.
    """
    try:
        with open(file, "rb") as _file:
            encoded_string = base64.b64encode(_file.read()).decode("utf-8")
        return encoded_string
    except Exception as e:
        print(f"Error al procesar el archivo {file}: {e}")
        return None

def generate_json_from_file(paths):
    """
    Genera una lista de diccionarios con los nombres de archivo y su contenido en base64.
    :param pdf_paths: Lista de rutas a archivos PDF.
    :return: Lista de diccionarios con los datos de los PDFs.
    """
    pdf_data = []
    for path in paths:
        if os.path.isfile(path) and path:
            base64_content = file_to_base64(path)
            if base64_content:
                pdf_data.append({
                    "file_name": os.path.basename(path),
                    "base64_content": base64_content
                })
        else:
            print(f"Archivo no encontrado o no es un PDF: {path}")
    
    return pdf_data  # Retorna una lista de diccionarios


if __name__ == "__main__":
    input_paths = [
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\- Factura 0003-00111312 -  - CARTOCOR S A .pdf",
        "D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png"
    ]

    result_data = generate_json_from_file(input_paths)

    # Imprimir el resultado
    print("Resultado:")
    for item in result_data:
        print(item)
