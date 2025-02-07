import unittest
from unittest.mock import patch, MagicMock
from src.services.tools.document_intelligence import process_base64_arrays

class TestDocumentProcessingAgent(unittest.TestCase):

    def setUp(self):
        # Configuración inicial
        self.base64_array = [
            "dGVzdCBkYXRhIGJhc2U2NA==",  # Base64 de "test data base64"
            "dGVzdCBkYXRhIGJhc2U2NA=="   # Base64 de "test data base64"
        ]
        self.fields_to_extract = ["invoice_number", "total_amount", "date"]

    @patch("src.agente_documentos.analyze_invoice_text")
    @patch("src.agente_documentos.analyze_invoice_vision")
    def test_successful_text_based_analysis(self, mock_analyze_vision, mock_analyze_text):
        # Simular resultados exitosos desde analyze_invoice_text
        mock_analyze_text.side_effect = [
            {"results": [{"field": "invoice_number", "value": "12345", "confidence": 0.95},
                         {"field": "total_amount", "value": "1000.00", "confidence": 0.92}],
             "missing_fields": [],
             "error": ""},
            {"results": [{"field": "invoice_number", "value": "67890", "confidence": 0.9},
                         {"field": "total_amount", "value": "1500.00", "confidence": 0.88}],
             "missing_fields": [],
             "error": ""}
        ]

        # Simular que no se llama a la herramienta basada en visión
        mock_analyze_vision.return_value = None

        # Ejecutar la función
        result = process_base64_arrays(self.base64_array, self.fields_to_extract)

        # Verificar los resultados
        self.assertEqual(len(result), 2)  # Dos documentos procesados
        self.assertEqual(result[0]["results"][0]["field"], "invoice_number")
        self.assertEqual(result[0]["results"][0]["value"], "12345")
        self.assertEqual(result[1]["results"][1]["value"], "1500.00")
        mock_analyze_text.assert_called()
        mock_analyze_vision.assert_not_called()

    @patch("src.agente_documentos.analyze_invoice_text")
    @patch("src.agente_documentos.analyze_invoice_vision")
    def test_fallback_to_vision_based_analysis(self, mock_analyze_vision, mock_analyze_text):
        # Simular resultados de analyze_invoice_text con campos faltantes
        mock_analyze_text.side_effect = [
            {"results": [{"field": "invoice_number", "value": "12345", "confidence": 0.95}],
             "missing_fields": ["total_amount"],
             "error": ""},
            {"results": [{"field": "invoice_number", "value": "67890", "confidence": 0.9}],
             "missing_fields": ["total_amount"],
             "error": ""}
        ]

        # Simular resultados exitosos desde analyze_invoice_vision
        mock_analyze_vision.side_effect = [
            {"results": [{"field": "total_amount", "value": "1000.00", "confidence": 0.88}],
             "missing_fields": [],
             "error": ""},
            {"results": [{"field": "total_amount", "value": "1500.00", "confidence": 0.86}],
             "missing_fields": [],
             "error": ""}
        ]

        # Ejecutar la función
        result = process_base64_arrays(self.base64_array, self.fields_to_extract)

        # Verificar los resultados
        self.assertEqual(len(result), 2)  # Dos documentos procesados
        self.assertEqual(result[0]["results"][0]["field"], "invoice_number")
        self.assertEqual(result[0]["results"][1]["field"], "total_amount")
        self.assertEqual(result[0]["results"][1]["value"], "1000.00")
        self.assertEqual(result[1]["results"][1]["value"], "1500.00")
        mock_analyze_text.assert_called()
        mock_analyze_vision.assert_called()

    @patch("src.agente_documentos.analyze_invoice_text")
    @patch("src.agente_documentos.analyze_invoice_vision")
    def test_handling_errors_in_analysis(self, mock_analyze_vision, mock_analyze_text):
        # Simular un error en analyze_invoice_text
        mock_analyze_text.side_effect = [
            {"results": [], "missing_fields": [], "error": "Error in text analysis"}
        ]

        # Simular un error en analyze_invoice_vision
        mock_analyze_vision.side_effect = [
            {"results": [], "missing_fields": [], "error": "Error in vision analysis"}
        ]

        # Ejecutar la función
        result = process_base64_arrays(self.base64_array, self.fields_to_extract)

        # Verificar los resultados
        self.assertEqual(len(result), 1)  # Un solo documento procesado
        self.assertEqual(result[0]["error"], "Error in text analysis")
        mock_analyze_text.assert_called()
        mock_analyze_vision.assert_called()


if __name__ == "__main__":
    unittest.main()
