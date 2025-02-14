import base64
import io
import pymupdf as fitz
from PIL import Image
from pdf2image import convert_from_bytes, convert_from_path

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

def pdf_page_to_base64(pdf_path: str, page_number: int):
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

def pdf_base64_to_image(pdf_base64: str, page_number: int):
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        pdf_stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        if page_number <= len(doc):
            page = doc[page_number - 1]  # Índice basado en 1
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            print(f"✅ Página {page_number} convertida desde base64 a imagen correctamente.")
            return img
        else:
            return None
    except Exception as e:
        print(f"❌ Error al convertir la página {page_number} desde base64 a imagen: {e}")
        return None

def pdf_base64_to_image_base64(pdf_base64: str, fin: int):
    conversiones = []
    for page_number in range(fin):
        image = pdf_base64_to_image(pdf_base64, page_number)
        if image is None:
            print(f"⚠️ No se pudo convertir la página {page_number} a base64 porque la imagen es inválida o se alcanzo el fin de archivo.")
            break

        try:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")
            print(f"✅ Página {page_number} convertida desde base64 a base64 correctamente.")
            conversiones.append(base64_string)
        except Exception as e:
            print(f"❌ Error al convertir la página {page_number} desde pdf base64 a imagen base64: {e}")
            break
    return conversiones


def pdf_binary_to_images(pdf_binary: bytes, fin: int):
    """
    Convierte un PDF en binario en una lista de imágenes en binario (PNG).

    :param pdf_binary: Contenido del PDF en binario.
    :param fin: Número máximo de páginas a procesar.
    :return: Lista de imágenes en binario (BytesIO).
    """
    conversiones = []

    try:
        images = convert_from_bytes(pdf_binary, first_page=1, last_page=fin)  # Convertir PDF a imágenes

        for page_number, image in enumerate(images):
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")  # Guardar en formato binario PNG
            buffer.seek(0)
            conversiones.append(buffer)
            print(f"✅ Página {page_number + 1} convertida desde binario a imagen binaria correctamente.")

    except Exception as e:
        print(f"❌ Error al convertir el PDF a imágenes: {e}")

    return conversiones