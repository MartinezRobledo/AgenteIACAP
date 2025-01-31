import unittest
import asyncio
from src.agents.agentClassifier import classifier, Input  # Ajusta el import según tu estructura de archivos

class TestClassifier(unittest.TestCase):
    def setUp(self):
        # Configuración del input inicial para las pruebas
        self.input_state = Input(
            asunto="Files attached to a message triggered a policy",
            cuerpo="""" 

Logo
[https://static-uk.mimecast.com/mimecast/resources/images/notifications/mimecast-logo-254x120.png]

 


FILES ATTACHED TO A MESSAGE TRIGGERED A POLICY

Contact your administrator if you need these files.

 

Message Details

 

From

""facturacion@proveedoresypf.com"" <facturacion@proveedoresypf.com>

To

Pedro Ibanez <pedro.ibanez@globaldata.com>

Subject

¡Hemos recibido tu consulta!  CAP-520263-L3X1Q3 - YPF-CAP:0001655533

Date

Wed, 15 Jan 2025 16:25:25 +0000

Policy

Default Attachment Management Definition - Block Dangerous File Types

Status

The message has been placed on HOLD - action required

 

File Details

 

- Attachment Policy (Default Attachment Management Definition - Block Dangerous
File Types)

Attachment Name: image.png
Policy Name: Default Attachment Management Definition - Block Dangerous File
Types
Detected as: png
Size: 57837 bytes
Action Taken: HOLD (Entire Message Held for Review)
Reason: Possible QR Image (100% probability), https://walink[.]co/013024


 

 

[https://static-uk.mimecast.com/mimecast/resources/images/notifications/powered-mimecast-logo-278x28.png]

 

© 2003 - 2025 Mimecast Services Limited and affiliates.

 

                                                           "
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

if __name__ == "__main__":
    unittest.main()
