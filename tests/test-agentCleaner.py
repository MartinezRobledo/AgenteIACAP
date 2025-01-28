import unittest
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage
from src.configs.classes import Input

# Nodo que limpia el cuerpo
def clean_body(state: Input, clean) -> Input:
    # Verifica si el estado es un diccionario con las claves necesarias
    if not isinstance(state, dict) or not all(key in state for key in ['asunto', 'cuerpo', 'adjuntos']):
        raise TypeError("El estado proporcionado no es un diccionario con las claves correctas.")
    
    cuerpo_filtrado = clean.invoke([HumanMessage(
        content=f"""Limpia el siguiente mail:\n
            {state['cuerpo']}
        """
    )])
    
    if not hasattr(cuerpo_filtrado, "content"):
        raise AttributeError("El objeto retornado por clean.invoke no tiene el atributo 'content'.")
    
    return Input(asunto=state['asunto'], cuerpo=cuerpo_filtrado.content, adjuntos=state['adjuntos'])

class TestCleanBodyNode(unittest.TestCase):

    def setUp(self):
        # Configuramos el mock para `clean.invoke`
        self.mock_clean = MagicMock()
        self.mock_clean.invoke = MagicMock()

    def test_clean_body_with_valid_input(self):
        # Simula un resultado limpio
        mock_response = MagicMock()
        mock_response.content = "Cuerpo limpio"
        self.mock_clean.invoke.return_value = mock_response

        # Input válido
        input_state = Input(asunto="Asunto prueba", cuerpo="Texto a limpiar", adjuntos="archivo.pdf")

        # Ejecutar el nodo
        result = clean_body(input_state, self.mock_clean)

        # Verificaciones
        self.assertTrue(isinstance(result, dict))
        self.assertIn('asunto', result)
        self.assertIn('cuerpo', result)
        self.assertIn('adjuntos', result)
        self.assertEqual(result['asunto'], "Asunto prueba")
        self.assertEqual(result['cuerpo'], "Cuerpo limpio")
        self.assertEqual(result['adjuntos'], "archivo.pdf")
        self.mock_clean.invoke.assert_called_once()

    def test_clean_body_with_empty_input(self):
        # Simula un resultado limpio
        mock_response = MagicMock()
        mock_response.content = "Cuerpo limpio"
        self.mock_clean.invoke.return_value = mock_response

        # Input vacío
        input_state = Input(asunto="", cuerpo="", adjuntos="")

        # Ejecutar el nodo
        result = clean_body(input_state, self.mock_clean)

        # Verificaciones
        self.assertTrue(isinstance(result, dict))
        self.assertIn('asunto', result)
        self.assertIn('cuerpo', result)
        self.assertIn('adjuntos', result)
        self.assertEqual(result['asunto'], "")
        self.assertEqual(result['cuerpo'], "Cuerpo limpio")
        self.assertEqual(result['adjuntos'], "")
        self.mock_clean.invoke.assert_called_once()

    def test_clean_body_handles_missing_content(self):
        # Simula un resultado sin `content`
        mock_response = MagicMock()
        del mock_response.content  # Eliminar explícitamente el atributo `content`
        self.mock_clean.invoke.return_value = mock_response

        # Input válido
        input_state = Input(asunto="Asunto prueba", cuerpo="Texto a limpiar", adjuntos="archivo.pdf")

        # Verifica que se levante el error esperado
        with self.assertRaises(AttributeError):
            clean_body(input_state, self.mock_clean)

if __name__ == '__main__':
    unittest.main()
