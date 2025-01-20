import json
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score

# Cargar los datos desde el archivo JSON
with open(r"D:\\Python\\agents\\app\\SkLearn\\Ejemplos.json", encoding='utf-8') as file:
    data = json.load(file)

# Extraer textos y categorías
X_texts = [item['Datos'] for item in data]
Y_categories = [item['Categoria'] for item in data]

# Limpiar los textos (remover caracteres especiales, URLs, imágenes, etc.)
def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)  # Remover etiquetas HTML
    text = re.sub(r'\[.*?\]', '', text)  # Remover contenido entre corchetes
    text = re.sub(r'http\S+|www\S+', '', text)  # Remover URLs
    text = re.sub(r'\n', ' ', text)  # Reemplazar saltos de línea por espacios
    text = re.sub(r'\s+', ' ', text)  # Remover espacios múltiples
    return text.strip().lower()

texts_cleaned = [clean_text(text) for text in X_texts]


# Dividir en conjunto de entrenamiento validacion y prueba
X_train, X_resto, y_train, y_resto = train_test_split(X_texts, Y_categories, test_size=0.2, random_state=123)
X_val, X_test, y_val, y_test = train_test_split(X_resto, y_resto, test_size=0.5, random_state=321)

# Convertir los textos a vectores TF-IDF
vectorizer = TfidfVectorizer(max_features=5000)  # Limitar a las 5000 palabras más relevantes
X_train_tfidf = vectorizer.fit_transform(X_train)
X_val_tfidf = vectorizer.fit_transform(X_val)
X_test_tfidf = vectorizer.transform(X_test)


# Entrenar el modelo Naive Bayes
model = MultinomialNB()
model.fit(X_train_tfidf, y_train)

# Predecir las categorías para el conjunto de prueba
y_pred = model.predict(X_test_tfidf)

# Evaluar el modelo
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))


# Clasificar un nuevo correo
new_email = """
Asunto: RE: Extranet de Proveedores
Cuerpo: Estimado, solicito estado de la factura 123456789.
"""
new_email_cleaned = clean_text(new_email)
new_email_tfidf = vectorizer.transform([new_email_cleaned])
predicted_category = model.predict(new_email_tfidf)
print("Predicted Category:", predicted_category[0])


import joblib

# Guardar el modelo y el vectorizador
joblib.dump(model, 'email_classifier.pkl')
joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')

# Cargar el modelo y el vectorizador para uso posterior
# model = joblib.load('email_classifier.pkl')
# vectorizer = joblib.load('tfidf_vectorizer.pkl')
