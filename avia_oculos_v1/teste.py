from gtts import gTTS
import miniaudio
import os
import cv2
import threading
import time
from rapidocr import RapidOCR

# --- CONFIG ---
INTERVAL = 2.0          # segundos entre cada OCR
MIN_CONF = 0.5          # confiança mínima do OCR
MIN_LEN = 8             # texto mínimo (evita ruído)
BLUR_MIN = 40           # nitidez mínima (descarta frames borrados)
DEBUG = True

# --- OCR ---
print("Carregando RapidOCR...")
ocr = RapidOCR(params={"Rec.lang_type": "pt"})
print("Pronto!")

# --- ESTADO ---
frame, lock = None, threading.Lock()
falando = False
auto = True             # NOVO: permite pausar/retomar
stop = False
status = "Aguardando"
proximo_ocr = 0.0


# --- UTIL ---
def nitidez(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def parece_fragmento(texto):
    """Texto curto sem pontuação final = provável fragmento."""
    palavras = len(texto.split())
    tem_pont = texto and texto[-1] in ".!?…"
    return palavras < 3 and not tem_pont


# --- ÁUDIO ---
def falar(texto):
    global falando
    falando = True
    try:
        if DEBUG:
            print(f"[FALA] {texto[:80]}")
        gTTS(text=texto, lang='pt', tld='com.br').save("tmp.mp3")
        with miniaudio.PlaybackDevice() as d:
            d.start(miniaudio.stream_file("tmp.mp3"))
            time.sleep(max(1.0, len(texto) * 0.08))
        os.remove("tmp.mp3")
    except Exception as e:
        print("Erro áudio:", e)
    finally:
        falando = False


# --- WORKER (OCR em thread separada) ---
def worker():
    global status, falando, stop, proximo_ocr, auto
    while not stop:
        time.sleep(0.1)

        if not auto:
            continue

        agora = time.time()
        if agora < proximo_ocr:
            continue

        if falando:
            continue

        with lock:
            img = frame.copy() if frame is not None else None
        if img is None:
            continue

        # Verifica nitidez
        n = nitidez(img)
        if n < BLUR_MIN:
            status = f"Borrado (nit={n:.0f}) — aproxime"
            proximo_ocr = agora + INTERVAL
            continue

        status = "Processando..."
        try:
            r = ocr(img)
            proximo_ocr = time.time() + INTERVAL

            if r is None or r.txts is None or len(r.txts) == 0:
                status = "Nenhum texto"
                continue

            textos = [t.strip() for t, s in zip(r.txts, r.scores)
                      if s >= MIN_CONF and t.strip()]

            if not textos:
                status = "Nenhum texto válido"
                continue

            texto_completo = " ".join(textos)

            if len(texto_completo) < MIN_LEN:
                status = "Muito curto"
                continue

            if parece_fragmento(texto_completo):
                status = f"Fragmento: {texto_completo[:30]}"
                continue

            # SEM verificação de "já falado" — relê sempre que aparecer
            status = f"Falando: {texto_completo[:35]}"
            threading.Thread(target=falar, args=(texto_completo,),
                             daemon=True).start()

        except Exception as e:
            print("Erro OCR:", e)
            proximo_ocr = time.time() + INTERVAL


# --- MAIN ---
def main():
    global frame, stop, status, auto
    cap = None
    for i in range(3):
        c = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if c.isOpened():
            cap = c
            print(f"Câmera {i}")
            break
        c.release()
    if not cap:
        print("Sem câmera")
        return

    threading.Thread(target=worker, daemon=True).start()
    print("p=pausar | q=sair")

    while True:
        ok, f = cap.read()
        if not ok:
            break
        with lock:
            frame = f.copy()

        # Indicador de nitidez
        try:
            n = nitidez(frame)
            cor_nit = (0, 255, 0) if n >= BLUR_MIN else (0, 0, 255)
            cv2.putText(f, f"nit={n:.0f}", (10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_nit, 1)
        except Exception:
            pass

        # Status (cinza se pausado, verde se ativo, vermelho se falando)
        if not auto:
            cor = (150, 150, 150)
            status_txt = "PAUSADO — aperte p para retomar"
        elif falando:
            cor = (0, 0, 255)
            status_txt = status
        else:
            cor = (0, 255, 0)
            status_txt = status

        cv2.putText(f, status_txt[:55], (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor, 2)
        cv2.putText(f, "p=pausar  q=sair", (10, f.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        cv2.imshow("Camera", f)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        elif k == ord('p'):
            auto = not auto
            print(f"Leitura {'ATIVADA' if auto else 'PAUSADA'}")

    stop = True
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()