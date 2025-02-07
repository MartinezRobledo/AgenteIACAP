import base64
import glob
import os
from src.configs.Prompt_Template import fields_to_extract
import pandas as pd
from src.services.tools.convert_pdf import pdf_base64_to_image_base64
from src.services.tools.document_intelligence import ImageFieldExtractor

INPUT_FILE = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Pruebas - caso individual.xlsx"
OUTPUT_FILE = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Casos - individuales - Resultados.xlsx"

def vision_call():
    # Cargar el archivo Excel
    df = pd.read_excel(INPUT_FILE)
    
    # Verificar que tenga las columnas necesarias
    if not {'Asunto', 'Cuerpo', 'IDCaso', 'ID'}.issubset(df.columns):
        raise ValueError("El archivo Excel debe contener las columnas 'Asunto', 'Cuerpo' e 'IDCaso' e 'ID'")
    

    for row in df.iterrows():
        case_id = row['IDCaso']
        id = row['ID']
        adjuntos_path = f"C:\\Users\Adrián\\Enta Consulting\\Optimización del CAP - General\\Adjuntos\\{case_id}"
        adjuntos_path_id = f"C:\\Users\Adrián\\Enta Consulting\\Optimización del CAP - General\\Adjuntos\\{id}"

        adjuntos_list = []
        if os.path.exists(adjuntos_path):
            for file_path in glob.glob(os.path.join(adjuntos_path, '*')):
                file_extension = os.path.splitext(file_path)[1].lower()

                if file_extension in ['.png', '.jpg', '.jpeg']:
                    with open(file_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                        adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})
                else:
                    with open(file_path, "rb") as doc_file:
                        encoded_string = base64.b64encode(doc_file.read()).decode("utf-8")
                        adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})
        elif os.path.exists(adjuntos_path_id):
            print("Busco por ID")
            for file_path in glob.glob(os.path.join(adjuntos_path_id, '*')):
                file_extension = os.path.splitext(file_path)[1].lower()

                if file_extension in ['.png', '.jpg', '.jpeg']:
                    print("Detecte la extensión")
                    with open(file_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                        adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})
                else:
                    with open(file_path, "rb") as doc_file:
                        encoded_string = base64.b64encode(doc_file.read()).decode("utf-8")
                        adjuntos_list.append({"file_name": os.path.basename(file_path), "base64_content": encoded_string})

    images_from_pdfs = []
    for file in adjuntos_list:
        pages = pdf_base64_to_image_base64(file["base64_content"], 10)
        for page in pages:
            image = {
                "file_name": file["file_name"],
                "base64_content": page
            }
            images_from_pdfs.append(image)
    extractor = ImageFieldExtractor()
    result = extractor.extract_fields(base64_images=images_from_pdfs, fields_to_extract=fields_to_extract)

    print("Resultado : ", result)

if __name__ == "__main__":
    vision_call()
