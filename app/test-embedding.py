from sentence_transformers import SentenceTransformer, util
import json

# Cargar el modelo
model = SentenceTransformer('all-MiniLM-L6-v2')  # Cambia el modelo según tus necesidades

# Cargar el JSON
with open("D:\\Python\\agents\\app\\SkLearn\\Ejemplos.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# Agrupar textos por categoría
category_texts = {}
for item in data:
    category = item["Categoria"]
    text = item["Datos"]
    if category not in category_texts:
        category_texts[category] = []
    category_texts[category].append(text)

# Función para categorizar un texto
def categorize_text(input_text):
    input_embedding = model.encode(input_text, convert_to_tensor=True)
    
    category_scores = {}
    for category, texts in category_texts.items():
        # Calcular embeddings para los textos de la categoría
        category_embeddings = model.encode(texts, convert_to_tensor=True)
        # Calcular la similitud máxima entre el texto de entrada y los textos de la categoría
        max_similarity = util.pytorch_cos_sim(input_embedding, category_embeddings).max().item()
        category_scores[category] = max_similarity
    
    # Devolver la categoría con mayor similitud
    best_category = max(category_scores, key=category_scores.get)
    return best_category, category_scores

# Texto de entrada
input_text = """

"""

# Clasificar el texto
predicted_category, scores = categorize_text(input_text)

# Resultados
print(f"Categoría predicha: {predicted_category}")
print(f"Puntajes de similitud: {scores}")
