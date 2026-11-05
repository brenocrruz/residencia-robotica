from gtts import gTTS
import miniaudio
import os
import cv2
from rapidocr import RapidOCR

# --- 1. CONFIGURAÇÃO DO AMBIENTE ---
print("Carregando modelo RapidOCR (IA local)...")
ocr = RapidOCR(params={"Rec.lang_type": "pt"})
print("Modelo carregado com sucesso!")

# --- 2. FUNÇÃO PARA CAPTURAR A IMAGEM ---
def capturar_imagem():
    camera = None
    for i in range(3):
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if cap.isOpened():
            camera = cap
            print(f"Câmera encontrada no índice {i}.")
            break
        cap.release()

    if camera is None:
        print("ERRO: Nenhuma câmera foi encontrada.")
        return None

    print("Pressione a tecla 's' para tirar a foto e 'q' para sair.")
    imagem_capturada = None
    while True:
        sucesso, frame = camera.read()
        if not sucesso:
            print("ERRO: Não foi possível ler o quadro da câmera.")
            break

        cv2.imshow("Camera", frame)
        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('s'):
            cv2.imwrite("foto_capturada.jpg", frame)
            imagem_capturada = "foto_capturada.jpg"
            print("Foto salva como 'foto_capturada.jpg'.")
            break
        elif tecla == ord('q'):
            print("Captura cancelada.")
            break

    camera.release()
    cv2.destroyAllWindows()
    return imagem_capturada

# --- 3. FUNÇÃO PARA LER O TEXTO DA IMAGEM (OCR com RapidOCR 3.x) ---
def ler_texto_da_imagem(caminho_imagem):
    if not caminho_imagem:
        return None

    print("Processando OCR com RapidOCR (IA)...")
    try:
        # O RapidOCR 3.x retorna um objeto RapidOCROutput.
        resultado = ocr(caminho_imagem)

        textos_reconhecidos = []

        # O objeto pode vir com .txts e .scores como None se nada for detectado.
        # Verificamos isso antes de acessar.
        if resultado and resultado.txts is not None:
            for texto, score in zip(resultado.txts, resultado.scores):
                if score > 0.5:  # Filtro de confiança
                    textos_reconhecidos.append(texto)

        texto_final = "\n".join(textos_reconhecidos)
        return texto_final.strip() if texto_final else None

    except Exception as e:
        print(f"ERRO durante o OCR: {e}")
        return None

# --- 4. FUNÇÃO PARA CONVERTER TEXTO EM ÁUDIO (TTS) ---
def falar_texto(texto):
    if not texto:
        return

    print("Gerando áudio (Google TTS)...")
    tts = gTTS(text=texto, lang='pt', tld='com.br', slow=False)
    arquivo_audio = "audio_temp.mp3"
    tts.save(arquivo_audio)

    print("Reproduzindo áudio...")
    stream = miniaudio.stream_file(arquivo_audio)

    with miniaudio.PlaybackDevice() as device:
        device.start(stream)
        input("Pressione Enter após o término do áudio...")

    try:
        os.remove(arquivo_audio)
    except OSError:
        pass

# --- 5. FLUXO PRINCIPAL DO PROGRAMA ---
if __name__ == "__main__":
    print("--- Iniciando Teste de Óculos Leitor ---")

    arquivo_imagem = capturar_imagem()
    # Para testar com uma imagem já salva, comente a linha acima e descomente a de baixo:
    # arquivo_imagem = "foto_capturada.jpg"

    if arquivo_imagem:
        texto_reconhecido = ler_texto_da_imagem(arquivo_imagem)

        if texto_reconhecido:
            print("\n--- Texto Reconhecido ---")
            print(texto_reconhecido)
            print("--------------------------\n")
            falar_texto(texto_reconhecido)
        else:
            print("Nenhum texto foi reconhecido na imagem.")

    print("--- Teste Finalizado ---")