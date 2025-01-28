import unittest
import asyncio
from src.agents.agentClassifier import classifier, Input  # Ajusta el import según tu estructura de archivos

class TestClassifier(unittest.TestCase):
    def setUp(self):
        # Configuración del input inicial para las pruebas
        self.input_state = Input(
            asunto="Consulta acceso Del Plata Ingenieria Austral",
            cuerpo="""
                Buen día, espero que se encuentren bien!
                Les escribo de Del Plata Ingeniería,
                Nosotros podemos acceder sin problemas al portal para consultar pagos de Del Plata Ingeniería S.A.:
                usuario: jolivares@dpisa.com.ar
                contraseña: Tigresa7

                Pero en Del Plata Ingenieria Autral S.A. (CUIT 30710984006) no podemos ingresar ya que no tenemos acceso al mail 
                con el que estábamos registrados porque esta persona no pertenece más a la empresa: lfernandez@dpisa.com.ar

                Queria saber como podemos ingresar para consultar los pagos de Del Plata Ingenieria Austral, si podemos gestionar 
                un nuevo usuario o agregar al usuario jolivares@dpisa.com.ar el acceso también a la otra cuenta.

                Muchas gracias!
            """,
            adjuntos=""
        )

    def test_classifier_output(self):
        async def run_classifier():
            messages = await classifier.ainvoke(self.input_state)
            return messages

        # Ejecutar la corutina usando asyncio.run
        result = asyncio.run(run_classifier())

        # Validar que el resultado contiene las claves esperadas
        self.assertIn("categoria", result)
        self.assertIn("data", result)

        # Validar que la categoría esperada está entre las opciones posibles
        self.assertIn(result["categoria"], [
            "Problemas de acceso",  # Categoría esperada para este caso
            "Alta de usuario"      # También es posible dependiendo del modelo
        ])

if __name__ == "__main__":
    unittest.main()
