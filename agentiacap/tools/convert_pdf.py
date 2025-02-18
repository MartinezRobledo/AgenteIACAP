import base64
import io
import pymupdf as fitz
from io import BytesIO


def render_pdf_page_as_image(pdf_path: str, page_number: int):
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]  # Índice basado en 1
        pix = page.get_pixmap()
        
        img_buffer = io.BytesIO()
        pix.save(img_buffer, "png")  # Guardar en PNG sin PIL
        img_buffer.seek(0)
        
        print(f"✅ Página {page_number} renderizada con PyMuPDF correctamente.")
        return img_buffer
    except Exception as e:
        print(f"❌ Error al renderizar la página {page_number} con PyMuPDF: {e}")
        return None

def pdf_base64_to_image_base64(pdf_base64: str, fin: int):
    conversiones = []
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        pdf_document = fitz.open("pdf", pdf_bytes)  # Cargar PDF desde base64

        for page_number in range(min(fin, len(pdf_document))):
            page = pdf_document[page_number]
            pix = page.get_pixmap()

            img_buffer = io.BytesIO()
            pix.save(img_buffer, "png")  # Guardar imagen en buffer
            img_buffer.seek(0)

            base64_string = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
            print(f"✅ Página {page_number + 1} convertida a base64 correctamente.")
            conversiones.append(base64_string)

    except Exception as e:
        print(f"❌ Error al convertir PDF a imágenes base64: {e}")

    return conversiones


def pdf_binary_to_images_base64(pdf_binary: bytes, dpi: int = 300):
    """
    Convierte un PDF escaneado en imágenes Base64 con resolución mejorada.
    """
    conversiones = []
    
    try:
        pdf_document = fitz.open(stream=pdf_binary, filetype="pdf")

        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))  # Ajuste de resolución
            
            # Convertir a bytes JPEG
            img_bytes = pix.tobytes("jpeg")  
            base64_image = base64.b64encode(img_bytes).decode("utf-8")

            # Verificación de imagen
            if not base64_image or len(base64_image) < 50:  # Umbral arbitrario
                print(f"❌ Error: Imagen Base64 inválida en la página {page_number + 1}")
                continue

            conversiones.append({
                "file_name": f"page_{page_number + 1}.jpg",
                "content": base64_image
            })

            print(f"✅ Página {page_number + 1} convertida correctamente.")

    except Exception as e:
        print(f"❌ Error al convertir PDF a imágenes: {e}")

    return conversiones