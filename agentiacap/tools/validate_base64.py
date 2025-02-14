import base64
import chardet

def detectar_codificacion(base64_string):
    """Intenta detectar la codificación del texto decodificado."""
    try:
        decoded_bytes = base64.b64decode(base64_string, validate=True)
        resultado = chardet.detect(decoded_bytes)
        return resultado.get("encoding", "Desconocida")
    except Exception:
        return "No se pudo determinar"

def probar_codificaciones(base64_string):
    """Prueba varias codificaciones para el Base64 y devuelve la decodificación exitosa."""
    codificaciones = ['utf-8', 'ascii', 'latin-1', 'utf-16']
    for codificacion in codificaciones:
        try:
            decoded_str = base64.b64decode(base64_string, validate=True).decode(codificacion)
            print(f"✅ Base64 decodificado exitosamente usando codificación {codificacion}.")
            return decoded_str
        except (base64.binascii.Error, UnicodeDecodeError):
            print(f"⚠️ No se pudo decodificar con codificación {codificacion}.")
    return None

def validar_base64(archivo_txt):
    """Valida si el contenido del archivo es un Base64 válido y detecta su tipo."""
    try:
        with open(archivo_txt, "r", encoding="utf-8") as file:
            base64_string = file.read().strip()

        # Si el base64 tiene un encabezado tipo "data:image/png;base64,", lo eliminamos
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]

        # Probar diferentes codificaciones y decodificar el Base64
        decoded_str = probar_codificaciones(base64_string)
        if decoded_str is None:
            print("❌ Error: El contenido no es un Base64 válido con las codificaciones probadas.")
            return

        # Detectar codificación del contenido decodificado
        encoding_detectado = detectar_codificacion(base64_string)
        print(f"🔠 Codificación detectada: {encoding_detectado}")

    except FileNotFoundError:
        print("❌ Error: Archivo no encontrado.")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

validar_base64("D:\Python\pruebas codificacion\FP-A-0006-00000743.txt")