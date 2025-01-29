import unittest
from unittest.mock import patch, MagicMock
from src.services.tools.document_intelligence import ImageFieldExtractor  # Ajusta la ruta según tu proyecto
import base64


class TestImageFieldExtractor(unittest.TestCase):

    @patch("src.services.tools.document_intelligence.AzureOpenAI")  # Mock de AzureOpenAI
    def test_extract_fields(self, mock_azure_openai):
        # Configura el mock del cliente de Azure OpenAI
        mock_client = MagicMock()
        mock_response = {
            "VendorName": "ACME Corp",
            "InvoiceDate": "2025-01-01",
            "InvoiceTotal": "1234.56"
        }
        mock_client.beta.chat.completions.parse.return_value.model_dump.return_value = mock_response
        mock_azure_openai.return_value = mock_client

        # Datos de prueba
        extractor = ImageFieldExtractor()
        with open("D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png", "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
        fields_to_extract = ["VendorName", "InvoiceDate", "InvoiceTotal"]

        # Llama al método bajo prueba
        result = extractor.extract_fields(base64_data, fields_to_extract)

        # Verifica el resultado
        self.assertEqual(result, mock_response)

    @patch("src.services.tools.document_intelligence.AzureOpenAI")  # Mock de AzureOpenAI
    def test_extract_fields_with_error(self, mock_azure_openai):
        # Configura el mock para simular un error
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = Exception("API error")
        mock_azure_openai.return_value = mock_client

        # Datos de prueba
        extractor = ImageFieldExtractor()
        with open("D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png", "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
        fields_to_extract = ["VendorName", "InvoiceDate", "InvoiceTotal"]

        # Llama al método bajo prueba
        result = extractor.extract_fields(base64_data, fields_to_extract)

        # Verifica el resultado
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API error")

class TestImageFieldExtractorRealAPI(unittest.TestCase):
    def test_real_api_call(self):
        """
        Realiza un llamado real a la API de Azure OpenAI para verificar los valores extraídos.
        """
        # Configuración del extractor con datos reales
        extractor = ImageFieldExtractor()

        # Cargar archivo de prueba (asegúrate de que exista en la ruta especificada)
        with open("D:\\Python\\agents\\tests\\Casos_de_adjuntos\\Sin título.png", "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")

        # Campos a extraer
        fields_to_extract = ["VendorName", "InvoiceDate", "InvoiceTotal"]

        # Llama al método de extracción
        result = extractor.extract_fields(base64_data, fields_to_extract)

        # Imprime el resultado para inspección manual
        print("Resultado de la API real:", result)

        # Asegúrate de que no haya errores en la respuesta
        self.assertNotIn("error", result, "La API devolvió un error.")
        self.assertTrue(isinstance(result, dict), "El resultado no es un diccionario.")


if __name__ == "__main__":
    unittest.main()
