from gtts import gTTS
import miniaudio, os, cv2, threading, time
from rapidocr import RapidOCR, EngineType

# --- CONFIG ---
STABLE_FRAMES = 10           # frames consecutivos estáveis (1s a 10Hz)
POLL_INTERVAL = 0.1          # segundos entre verificações
MOTION_THRESHOLD = 5.0       # mean diff abaixo disso = frame estável
SCENE_CHANGE = 20.0          # mean diff acima disso = cena diferente
COOLDOWN = 1.5               # pausa após falar
MIN_CONF = 0.5
MIN_LEN = 5
LINHA_Y_TOL = 15
PARA_GAP_RATIO = 0.6
BLUR_MIN_VAR = 60            # nitidez mínima (variância do Laplaciano)
DEBUG = True

# --- OCR ---
print("Carregando RapidOCR...")
ocr = RapidOCR(params={
    "Det.engine_type": EngineType.OPENVINO,
    "Cls.engine_type": EngineType.OPENVINO,
    "Rec.engine_type": EngineType.OPENVINO,
    "Rec.lang_type": "pt",
})
print("Pronto!")

# --- ESTADO ---
frame, lock = None, threading.Lock()
falando = False
auto = True
stop = False
status = "Aponte para o texto"
ultimas_boxes = []


# ============================================================
# ÁUDIO
# ============================================================
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


# ============================================================
# UTILITÁRIOS DE IMAGEM
# ============================================================
def _prep(img):
    """Reduz para 128x128 em grayscale + blur. Remove ruído de LED/sensor."""
    small = cv2.resize(img, (128, 128))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def diferenca(img1, img2):
    """Diferença MÉDIA entre dois frames (escala 0-255)."""
    if img2 is None:
        return 255.0
    return float(cv2.absdiff(_prep(img1), _prep(img2)).mean())


def nitidez(img):
    """Variância do Laplaciano. Quanto maior, mais nítida."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


# ============================================================
# PROCESSAMENTO (uma passada)
# ============================================================
def processar(img):
    """OCR + layout. Retorna (textos_em_ordem, boxes_para_desenhar)."""
    r = ocr(img)
    if r is None or r.txts is None or len(r.txts) == 0:
        return [], []

    boxes = list(r.boxes) if r.boxes is not None else []
    linhas = []
    boxes_draw = []

    for i, (txt, sc) in enumerate(zip(r.txts, r.scores)):
        if sc < MIN_CONF or not txt.strip() or len(txt.strip()) < MIN_LEN:
            continue
        if i >= len(boxes) or boxes[i] is None:
            continue
        ys = [float(p[1]) for p in boxes[i]]
        xs = [float(p[0]) for p in boxes[i]]
        linhas.append({
            'txt': txt.strip(),
            'y_min': min(ys), 'y_max': max(ys),
            'x_min': min(xs), 'x_max': max(xs),
        })
        boxes_draw.append((int(min(xs)), int(min(ys)),
                           int(max(xs)), int(max(ys))))

    if not linhas:
        return [], boxes_draw

    linhas.sort(key=lambda l: l['y_min'])

    grupos = [[linhas[0]]]
    for l in linhas[1:]:
        prev = grupos[-1][-1]
        gap = l['y_min'] - prev['y_max']
        alt = ((prev['y_max'] - prev['y_min']) + (l['y_max'] - l['y_min'])) / 2
        if gap > alt * PARA_GAP_RATIO:
            grupos.append([l])
        else:
            grupos[-1].append(l)

    textos = []
    for g in grupos:
        g.sort(key=lambda l: l['y_min'])
        linhas_visuais = [[g[0]]]
        for l in g[1:]:
            if abs(l['y_min'] - linhas_visuais[-1][0]['y_min']) < LINHA_Y_TOL:
                linhas_visuais[-1].append(l)
            else:
                linhas_visuais.append([l])
        partes = []
        for lv in linhas_visuais:
            lv.sort(key=lambda l: l['x_min'])
            partes.append(" ".join(l['txt'] for l in lv))
        textos.append(" ".join(partes))

    return textos, boxes_draw


# ============================================================
# WORKER (estabilização por frames consecutivos)
# ============================================================
def worker():
    global status, falando, ultimas_boxes, auto, stop
    frame_ant = None
    estavel_count = 0
    ultimo_trigger = None
    cooldown_ate = 0

    while not stop:
        time.sleep(POLL_INTERVAL)

        if not auto or falando:
            frame_ant = None
            estavel_count = 0
            continue

        with lock:
            img = frame.copy() if frame is not None else None
        if img is None:
            continue

        # 1. Verifica nitidez
        n = nitidez(img)
        if n < BLUR_MIN_VAR:
            status = f"Borrado (nit={n:.0f})"
            frame_ant = img
            estavel_count = 0
            continue

        if frame_ant is None:
            frame_ant = img
            continue

        # 2. Calcula diferença com o frame ANTERIOR (não com referência fixa)
        diff = diferenca(img, frame_ant)
        frame_ant = img

        # 3. Conta frames consecutivos estáveis
        if diff < MOTION_THRESHOLD:
            estavel_count += 1
        else:
            estavel_count = 0

        status = f"Estável {estavel_count}/{STABLE_FRAMES} (mov={diff:.1f} nit={n:.0f})"

        if estavel_count < STABLE_FRAMES:
            continue

        agora = time.time()
        if agora < cooldown_ate:
            continue

        # 4. Evita reler a mesma cena
        if ultimo_trigger is not None and diferenca(img, ultimo_trigger) < SCENE_CHANGE:
            status = "Mesmo texto — mova para outro"
            continue

        # 5. Processa
        status = "Processando..."
        textos, boxes = processar(img)
        ultimas_boxes = boxes

        if not textos:
            status = "Nenhum texto detectado"
            ultimo_trigger = img.copy()
            cooldown_ate = time.time() + COOLDOWN
            estavel_count = 0
            continue

        ultimo_trigger = img.copy()

        for t in textos:
            status = f"Falando: {t[:35]}"
            falar(t)

        status = "Concluído — mova para outro texto"
        cooldown_ate = time.time() + COOLDOWN
        estavel_count = 0


# ============================================================
# MAIN
# ============================================================
def main():
    global frame, auto, stop
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

        for (x1, y1, x2, y2) in ultimas_boxes:
            cv2.rectangle(f, (x1, y1), (x2, y2), (255, 255, 0), 1)

        cor = (0, 0, 255) if falando else (0, 255, 0) if auto else (0, 165, 255)
        cv2.putText(f, status[:60], (10, 25),
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