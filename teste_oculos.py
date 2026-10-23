from gtts import gTTS
import miniaudio
import os
import cv2
import pytesseract
import pyttsx3
from PIL import Image

# --- 1. CONFIGURAÇÃO DO AMBIENTE ---
# Informe ao Python onde o motor Tesseract foi instalado.
# Se você instalou no caminho padrão, esta linha é suficiente.
# Se instalou em outro lugar, ajuste o caminho entre as aspas.
caminho_tesseract = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = caminho_tesseract

# Define o idioma que o Tesseract deve usar para ler o texto.
IDIOMA_OCR = 'por' # 'por' é o código para Português.

#--- 2. FUNÇÃO PARA CAPTURAR A IMAGEM ---
def capturar_imagem():
    # Tenta abrir a câmera nos primeiros índices (0, 1, 2).
    # Isso ajuda caso a webcam padrão do notebook não seja a câmera endoscópica.
    camera = None
    for i in range(3):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        #cap = cv2.VideoCapture(i)
        if cap.isOpened():
            camera = cap
            print(f"Câmera encontrada no índice {i}.")
            break
        cap.release()

    if camera is None:
        print("ERRO: Nenhuma câmera foi encontrada.")
        return None

    # Mostra o vídeo da câmera em uma janela.
    print("Pressione a tecla 's' para tirar a foto e 'q' para sair.")
    imagem_capturada = None
    while True:
        # Lê um quadro (frame) do vídeo.
        sucesso, frame = camera.read()
        if not sucesso:
            print("ERRO: Não foi possível ler o quadro da câmera.")
            break

        # Exibe o quadro na janela "Camera".
        cv2.imshow("Camera", frame)

        # Espera por uma tecla ser pressionada.
        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('s'):
            # Se 's' for pressionado, salva o quadro atual.
            cv2.imwrite("foto_capturada.jpg", frame)
            imagem_capturada = "foto_capturada.jpg"
            print("Foto salva como 'foto_capturada.jpg'.")
            break
        elif tecla == ord('q'):
            # Se 'q' for pressionado, sai do loop.
            print("Captura cancelada.")
            break

    # Libera a câmera e fecha todas as janelas do OpenCV.
    camera.release()
    cv2.destroyAllWindows()
    return imagem_capturada

# --- 3. FUNÇÃO PARA LER O TEXTO DA IMAGEM (OCR) ---
def ler_texto_da_imagem(caminho_imagem):
    if not caminho_imagem:
        return None

    print("Processando OCR...")
    try:
        # Abre a imagem usando a biblioteca Pillow.
        imagem = Image.open(caminho_imagem)
        # Chama o Tesseract para extrair o texto.
        # lang='por' garante que ele use o dicionário de português.
        texto = pytesseract.image_to_string(imagem, lang=IDIOMA_OCR)
        return texto.strip() # .strip() remove espaços em branco extras.
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
    
    # Abre o arquivo de áudio e cria um stream de reprodução
    stream = miniaudio.stream_file(arquivo_audio)
    
    # O bloco 'with' garante que o dispositivo de áudio seja liberado no final
    with miniaudio.PlaybackDevice() as device:
        device.start(stream)
        # O input() faz o programa esperar até você apertar Enter.
        # Assim, o áudio toca por completo antes de o código continuar.
        input("Pressione Enter após o término do áudio...")
    
    # Remove o arquivo
    try:
        os.remove(arquivo_audio)
    except OSError:
        pass

# --- 5. FLUXO PRINCIPAL DO PROGRAMA ---
if __name__ == "__main__":
    print("--- Iniciando Teste de Óculos Leitor ---")
    
    # Passo 1: Capturar a imagem.
    arquivo_imagem = capturar_imagem()
    #arquivo_imagem = r"C:\Users\Breno Cruz\Desktop\pasta-cruz\dev\residencia-robotica\foto_capturada.jpg"
    
    if arquivo_imagem:
        # Passo 2: Ler o texto.
        texto_reconhecido = ler_texto_da_imagem(arquivo_imagem)
        
        if texto_reconhecido:
            print("\n--- Texto Reconhecido ---")
            print(texto_reconhecido)
            print("--------------------------\n")
            
            # Passo 3: Falar o texto.
            falar_texto(texto_reconhecido)
        else:
            print("Nenhum texto foi reconhecido na imagem.")
    
    print("--- Teste Finalizado ---")