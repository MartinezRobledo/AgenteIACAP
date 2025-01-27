import unittest
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage
from src.configs.llms import llm4o_mini
from src.configs.classes import Input

# Mock de cleaner
mock_clean = MagicMock()
mock_clean.invoke = MagicMock(return_value=MagicMock(content="Cuerpo limpio"))

class TestCleanBodyNode(unittest.TestCase):
    def setUp(self):
        # Inicializamos el mock en lugar de clean
        self.clean = mock_clean

    def test_clean_body_with_valid_input(self):
        # Input válido
        input_state = Input(asunto="Asunto prueba", cuerpo="Este es el cuerpo original", adjuntos="archivo.pdf")
        
        # Nodo que limpia el cuerpo
        def clean_body(state: Input) -> Input:
            cuerpo_filtrado = self.clean.invoke([HumanMessage(
                content=f"""Limpia el siguiente mail:\n
                    {state.cuerpo}
                """
            )])
            return Input(asunto=state.asunto, cuerpo=cuerpo_filtrado.content, adjuntos=state.adjuntos)

        # Ejecutar el nodo
        result = clean_body(input_state)

        # Verificaciones
        self.assertIsInstance(result, Input)
        self.assertEqual(result.asunto, "Asunto prueba")
        self.assertEqual(result.cuerpo, "Cuerpo limpio")
        self.assertEqual(result.adjuntos, "archivo.pdf")
        self.clean.invoke.assert_called_once()

    def test_clean_body_with_empty_input(self):
        # Input vacío
        input_state = Input(asunto="", cuerpo="", adjuntos="")
        
        # Nodo que limpia el cuerpo
        def clean_body(state: Input) -> Input:
            cuerpo_filtrado = self.clean.invoke([HumanMessage(
                content=f"""Limpia el siguiente mail:\n
                    {state.cuerpo}
                """
            )])
            return Input(asunto=state.asunto, cuerpo=cuerpo_filtrado.content, adjuntos=state.adjuntos)

        # Ejecutar el nodo
        result = clean_body(input_state)

        # Verificaciones
        self.assertIsInstance(result, Input)
        self.assertEqual(result.asunto, "")
        self.assertEqual(result.cuerpo, "Cuerpo limpio")  # Siempre retorna "Cuerpo limpio" en este test
        self.assertEqual(result.adjuntos, "")
        self.clean.invoke.assert_called_once()

    def test_clean_body_handles_missing_content(self):
        # Modificar el mock para devolver un objeto sin 'content'
        self.clean.invoke = MagicMock(return_value=MagicMock())

        input_state = Input(asunto="Test", cuerpo="Texto original", adjuntos="archivo.pdf")

        # Nodo que limpia el cuerpo
        def clean_body(state: Input) -> Input:
            cuerpo_filtrado = self.clean.invoke([HumanMessage(
                content=f"""Limpia el siguiente mail:\n
                    {state.cuerpo}
                """
            )])
            if not hasattr(cuerpo_filtrado, "content"):
                raise AttributeError("El objeto retornado por clean.invoke no tiene el atributo 'content'.")
            return Input(asunto=state.asunto, cuerpo=cuerpo_filtrado.content, adjuntos=state.adjuntos)

        # Ejecutar y verificar que lanza un error
        with self.assertRaises(AttributeError):
            clean_body(input_state)

if __name__ == '__main__':
    unittest.main()
