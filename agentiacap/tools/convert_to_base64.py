import base64
import sys

def image_to_base64(image_path, output_file):
    try:
        with open(image_path, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode("utf-8")
        
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(base64_data)

        print(f"Conversión exitosa. Base64 guardado en: {output_file}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python convert_to_base64.py <ruta_imagen> <archivo_salida>")
    else:
        image_to_base64(sys.argv[1], sys.argv[2])
