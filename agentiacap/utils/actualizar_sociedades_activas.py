import pandas as pd

def excel_to_list(file_path):
    # Cargar el archivo Excel
    df = pd.read_excel(file_path, dtype=str)
    
    # Seleccionar las columnas requeridas
    columnas = {
        "NOMBRE SAP": "Nombre Soc SAP",
        "Código SAP": "Código SAP",
        "Estado": "Estado",
        "CUIT": "CUIT",
        "Nombre ARCA/AFIP": "Nombre en AFIP"
    }
    
    # Filtrar y renombrar las columnas
    df = df[list(columnas.keys())].rename(columns=columnas)
    
    # Convertir el DataFrame en una lista de diccionarios
    lista_objetos = df.to_dict(orient='records')
    
    return lista_objetos

# Ejemplo de uso
if __name__ == "__main__":
    file_path = "C:\\Users\\Adrián\\Enta Consulting\\Optimización del CAP - General\\Sociedades activas SAP_03-2025.xlsx"  # Reemplaza con el nombre real del archivo
    resultado = excel_to_list(file_path)
    print(resultado)
