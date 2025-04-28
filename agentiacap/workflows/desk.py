import json
from agentiacap.llms.Prompts import TextExtractorPrompt
from agentiacap.llms.llms import llm4o
from agentiacap.utils.globals import lista_sociedades


socs = [soc["Nombre Soc SAP"] for soc in lista_sociedades] + [soc["Nombre en AFIP"] for soc in lista_sociedades]
cods_soc = [soc["Código SAP"] for soc in lista_sociedades]
cuits = [soc["CUIT"] for soc in lista_sociedades]

json_schema_names = {
    "name": "fixer_schema",
    "schema": {
        "type": "object",
        "properties": {
            "final_answer": {
                "type": "object",
                "properties": {
                    "VendorName": {"type": ["string", "null"]},
                    "CustomerName": {"type": ["string", "null"],
                                    "enum": socs},
                    "CustomerTaxId": {"type": ["string", "null"],
                                    "enum": cuits},
                    "CustomerCodSap": {"type": ["string", "null"],
                                    "enum": cods_soc},
                    "VendorTaxId": {"type": ["string", "null"]}
                },
                "required": [
                    "VendorName", "CustomerName", "CustomerTaxId", "CustomerCodSap", 
                    "VendorTaxId"
                ],
                "additionalProperties": False
            }
        },
        "required": ["final_answer"],
        "additionalProperties": False
    },
    "strict": True
}

prompt = [
    {"role": "system", 
        "content": TextExtractorPrompt.names_and_cuits_prompt},
        {"role": "user",
        "content": "Dado el siguiente texto de un mail extrae el dato pedido: Buen día me llamo Adrián y quiero saber el estado de las facturas adjuntas."}
]
result = llm4o.generate(
    messages=[prompt], 
    response_format={
    "type": "json_schema",
    "json_schema": json_schema_names
    }
)
result = json.loads(result.generations[0][0].text.strip())["final_answer"]

print(result)