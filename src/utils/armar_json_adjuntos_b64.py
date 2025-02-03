import base64
import io
from PIL import Image
from pdf2image import convert_from_path
import fitz

def pdf_page_to_image(pdf_path: str, page_number: int):
    try:
        images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
        if images:
            print(f"✅ Página {page_number} convertida a imagen correctamente.")
            return images[0]  # Retorna la imagen de la página
        else:
            print(f"⚠️ No se pudo extraer la imagen de la página {page_number}, intentando renderizar con PyMuPDF.")
            return render_pdf_page_as_image(pdf_path, page_number)
    except Exception as e:
        print(f"❌ Error al convertir la página {page_number} a imagen: {e}")
        return None

def render_pdf_page_as_image(pdf_path: str, page_number: int):
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]  # Índice basado en 1
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        print(f"✅ Página {page_number} renderizada con PyMuPDF correctamente.")
        return img
    except Exception as e:
        print(f"❌ Error al renderizar la página {page_number} con PyMuPDF: {e}")
        return None

def pdf_to_base64(pdf_path: str, page_number: int):
    image = pdf_page_to_image(pdf_path, page_number)
    if image is None:
        print(f"⚠️ No se pudo convertir la página {page_number} a base64 porque la imagen es inválida.")
        return None
    
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")
        print(f"✅ Página {page_number} convertida a base64 correctamente.")
        return base64_string
    except Exception as e:
        print(f"❌ Error al convertir la página {page_number} a base64: {e}")
        return None
