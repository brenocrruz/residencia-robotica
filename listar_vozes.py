import pyttsx3

engine = pyttsx3.init()
vozes = engine.getProperty('voices')

print("--- VOZES DISPONÍVEIS ---")
for i, voz in enumerate(vozes):
    print(f"Índice: {i}")
    print(f"ID: {voz.id}")
    print(f"Nome: {voz.name}")
    print(f"Idiomas: {voz.languages}")
    print("-" * 30)