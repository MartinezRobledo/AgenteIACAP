import re

def validate_invoice(invoice_number: str) -> str:
    """
    Valida si un número de factura cumple con el formato esperado.
    """
    pattern = r"(?:^|(?<=\s))([ABCMTE]?\d{0,4}[ABCMTE\-]?\d{1,8})(?=\s|$)"      # Ejemplo: 4 dígitos - 8 dígitos (1234-56789012)

    if re.fullmatch(pattern, invoice_number):
        return "El número de factura es válido."
    else:
        return "El número de factura no cumple con el formato esperado."