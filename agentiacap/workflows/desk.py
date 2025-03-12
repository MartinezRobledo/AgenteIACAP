import asyncio

async def funcA():
    await asyncio.sleep(4)
    return "Resultado A"

async def funcB():
    await asyncio.sleep(2)
    return "Resultado B"

async def funcC():
    await asyncio.sleep(3)
    return "Resultado C"

async def ejecutar():
    # Lanzamos las funciones en paralelo y esperamos sus resultados
    resultados = await asyncio.gather(funcA(), funcB(), funcC())

    # Guardamos los resultados en variables
    resultado1, resultado2, resultado3 = resultados
    
    # Imprimimos los resultados
    print(resultado1)
    print(resultado2)
    print(resultado3)

# Ejecutar la función principal
asyncio.run(ejecutar())
