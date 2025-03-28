import re

notas = [{"file_name": "Test/Firmas/Nota modelo-Devolución de Retenciones2000091532_signed_Caso 10.pdf-page_1.jpg"}]

archivos = [re.search(r'(?<=/)([^/]+?)(?:-page_\d+)?(?=\.jpg)', n["file_name"]).group() for n in notas]

print(archivos)