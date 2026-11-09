# main.py
import cv2
import threading
import time
import difflib

from audio_manager import AudioManager
from ocr_engine import OCREngine
import config

# Variáveis globais compartilhadas
frame_atual = None
lock = threading.Lock()
ultimo_texto_falado = ""
parar_programa = False

def thread_ocr(ocr_engine, audio_manager):
    global ultimo_texto_falado, frame_atual, parar_programa
    estado_atual = "BUSCANDO" 
    
    while not parar_programa:
        time.sleep(config.TEMPO_ESPERA_OCR)
        
        if audio_manager.falando:
            continue
            
        with lock:
            if frame_atual is None:
                continue
            img_para_ler = frame_atual.copy()
        
        texto_completo = ocr_engine.processar(img_para_ler)
        
        if len(texto_completo) > 0:
            print(f"[IA CAPTUROU]: '{texto_completo}'")
        
        if len(texto_completo) > 5:
            similaridade = difflib.SequenceMatcher(None, ultimo_texto_falado, texto_completo).ratio()
            
            if similaridade < config.SIMILARIDADE_MINIMA: 
                ultimo_texto_falado = texto_completo
                
                if estado_atual == "BUSCANDO":
                    estado_atual = "LENDO"
                    texto_para_falar = "Texto encontrado. Lendo: " + texto_completo
                else:
                    texto_para_falar = texto_completo
                    
                threading.Thread(target=audio_manager.falar, args=(texto_para_falar,), daemon=True).start()
        else:
            if estado_atual == "LENDO":
                estado_atual = "BUSCANDO"
                print("\n[ESTADO] Texto sumiu. Voltando a procurar...")
                threading.Thread(target=audio_manager.falar, args=("Procurando texto",), daemon=True).start()


def iniciar_camera():
    global frame_atual, parar_programa
    
    audio_manager = AudioManager()
    ocr_engine = OCREngine()
    
    camera = None
    
    # Lógica inteligente de seleção de câmera:
    # Se CAMERA_INDEX foi definido no config, testa apenas ele.
    # Se for None, testa primeiro as externas (1 e 2) e deixa a webcam do notebook (0) por último.
    if config.CAMERA_INDEX is not None:
        indices_para_testar = [config.CAMERA_INDEX]
    else:
        indices_para_testar = [1, 2, 0] # Prioriza câmeras externas (endoscópio)
    
    for i in indices_para_testar:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            camera = cap
            print(f"Câmera encontrada no índice {i}.")
            break
        cap.release()

    if camera is None:
        print("ERRO: Nenhuma câmera encontrada.")
        return

    # Inicia as threads
    threading.Thread(target=thread_ocr, args=(ocr_engine, audio_manager), daemon=True).start()
    threading.Thread(target=audio_manager.falar, args=("Procurando texto",), daemon=True).start()
    
    print("\n--- MODO TEMPO REAL ATIVADO ---")
    print("Pressione 'q' na janela para encerrar.")

    while True:
        sucesso, frame = camera.read()
        if not sucesso:
            break

        with lock:
            frame_atual = frame.copy()

        if audio_manager.falando:
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
if __name__ == "__main__":
    iniciar_camera()
    print("--- Apresentação Finalizada ---")