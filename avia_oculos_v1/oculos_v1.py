from gtts import gTTS
import miniaudio
import os
import cv2
import threading
import time
import difflib
import glob
from rapidocr import RapidOCR

# --- 1. CONFIGURAÇÕES E LIMPEZA ---
print("Limpando arquivos de áudio antigos...")
for f in glob.glob("audio_*.mp3"):
    try: os.remove(f)
    except: pass

print("Carregando modelo RapidOCR (IA local)...")
ocr = RapidOCR(params={"Rec.lang_type": "pt"})
print("Modelo carregado com sucesso!")

# Variáveis globais
frame_atual = None
lock = threading.Lock()
falando = False
ultimo_texto_falado = ""
parar_programa = False

# --- 2. FUNÇÃO DE ÁUDIO (CORRIGIDA) ---
def falar_texto(texto):
    global falando
    if falando or not texto:
        return
    
    falando = True
    nome_arquivo = f"audio_{int(time.time() * 1000)}.mp3"
    
    try:
        print(f"\n[AUDIO] Falando: '{texto[:60]}...'")
        tts = gTTS(text=texto, lang='pt', tld='com.br', slow=False)
        tts.save(nome_arquivo)

        # Obtém a duração EXATA do áudio gerado
        info = miniaudio.get_file_info(nome_arquivo)
        duracao = info.duration  # em segundos

        # Reproduz o áudio
        stream = miniaudio.stream_file(nome_arquivo)
        with miniaudio.PlaybackDevice() as device:
            device.start(stream)
            # Espera a duração exata + uma pequena margem de segurança (0.2s)
            time.sleep(duracao + 0.2)
            
    except Exception as e:
        print(f"Erro no áudio: {e}")
    finally:
        falando = False
        try:
            if os.path.exists(nome_arquivo):
                os.remove(nome_arquivo)
        except PermissionError:
            pass

# --- 3. PRÉ-PROCESSAMENTO DE IMAGEM (NOVO) ---
def melhorar_imagem(img):
    """Aumenta o contraste e reduz ruído para ajudar o OCR da câmera de endoscópio."""
    # Converte para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Aplica equalização de histograma para melhorar o contraste
    eq = cv2.equalizeHist(gray)
    # Aplica um leve desfoque para reduzir ruído de sensor
    blur = cv2.GaussianBlur(eq, (3, 3), 0)
    return blur

# --- 4. THREAD DE LEITURA ---
def thread_ocr():
    global ultimo_texto_falado, frame_atual, parar_programa
    estado_atual = "BUSCANDO" 
    
    while not parar_programa:
        time.sleep(2.0)
        
        if falando:
            continue
            
        with lock:
            if frame_atual is None:
                continue
            img_para_ler = frame_atual.copy()
        
        try:
            # Aplica o pré-processamento antes de enviar para a IA
            img_processada = melhorar_imagem(img_para_ler)
            
            resultado = ocr(img_processada)
            textos = []
            if resultado and resultado.txts is not None:
                for texto, score in zip(resultado.txts, resultado.scores):
                    if score > 0.6:
                        textos.append(texto)
            
            texto_completo = " ".join(textos).strip()
            
            if len(texto_completo) > 0:
                print(f"[IA CAPTUROU]: '{texto_completo}'")
            
            if len(texto_completo) > 5:
                similaridade = difflib.SequenceMatcher(None, ultimo_texto_falado, texto_completo).ratio()
                
                if similaridade < 0.75: 
                    ultimo_texto_falado = texto_completo
                    
                    if estado_atual == "BUSCANDO":
                        estado_atual = "LENDO"
                        texto_para_falar = "Texto encontrado. Lendo: " + texto_completo
                    else:
                        texto_para_falar = texto_completo
                        
                    threading.Thread(target=falar_texto, args=(texto_para_falar,), daemon=True).start()
            else:
                if estado_atual == "LENDO":
                    estado_atual = "BUSCANDO"
                    print("\n[ESTADO] Texto sumiu. Voltando a procurar...")
                    threading.Thread(target=falar_texto, args=("Procurando texto",), daemon=True).start()
                    
        except Exception as e:
            print(f"Erro no OCR: {e}")

# --- 5. LOOP PRINCIPAL ---
def iniciar_camera():
    global frame_atual, parar_programa
    
    camera = None
    for i in range(3):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            camera = cap
            print(f"Câmera encontrada no índice {i}.")
            break
        cap.release()

    if camera is None:
        print("ERRO: Nenhuma câmera encontrada.")
        return

    threading.Thread(target=thread_ocr, daemon=True).start()
    threading.Thread(target=falar_texto, args=("Procurando texto",), daemon=True).start()
    
    print("\n--- MODO TEMPO REAL ATIVADO ---")
    print("Pressione 'q' na janela para encerrar.")

    while True:
        sucesso, frame = camera.read()
        if not sucesso:
            break

        with lock:
            frame_atual = frame.copy()

        if falando:
            cor = (0, 0, 255)
            status = "FALANDO..."
        else:
            cor = (0, 255, 0)
            status = "PROCURANDO TEXTO..."
            
        cv2.putText(frame, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)
        cv2.putText(frame, "Pressione 'q' para sair", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Oculos Leitor - Tempo Real", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    parar_programa = True
    camera.release()
    cv2.destroyAllWindows()

# --- 6. EXECUÇÃO ---
if __name__ == "__main__":
    iniciar_camera()
    print("--- Apresentação Finalizada ---")