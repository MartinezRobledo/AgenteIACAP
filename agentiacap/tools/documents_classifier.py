from fastapi import logger
from agentiacap.tools.convert_pdf import pdf_binary_to_images_base64
from agentiacap.tools.document_intelligence import ImageFieldExtractor


def wrapper_es_carta_modelo(state):
    try:
        images_from_pdfs = []
        for file in state["pdfs"]:
            file_name = file["file_name"]
            content = file.get("content", b"")
            pages = pdf_binary_to_images_base64(content, dpi=300)
            for page in pages:
                page_name = page["file_name"]
                image = {
                    "file_name": f"{file_name}-{page_name}",
                    "content": page["content"]
                }
                images_from_pdfs.append(image)
        extractor = ImageFieldExtractor()
        result = extractor.es_carta_modelo(base64_images=images_from_pdfs)
        
        return result
    except Exception as e:
        logger.error(f"Error en 'wrapper_es_carta_modelo': {str(e)}")
        raise

# path_pdf = "D:\\Python\\AgentIACAP\\tests\\Ejemplo carta modelo.pdf"

# with open(path_pdf, "rb") as file:
#     content = file.read()

# result = wrapper_es_carta_modelo({"file_name":"Ejemplo carta modelo.pdf", "content":content})

# print(result)