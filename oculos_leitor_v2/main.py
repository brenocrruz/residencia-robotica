"""Modo de terminal do Óculos Leitor V2 (sem interface gráfica)."""

import cv2
import time
import config
from reader_pipeline import ReaderPipeline


def abrir_camera():
    indices = [config.CAMERA_INDEX] if config.CAMERA_INDEX is not None else [1, 2, 0]
    backend = cv2.CAP_DSHOW if config.CAMERA_BACKEND_DSHOW else cv2.CAP_ANY
    for index in indices:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
            print(f"[CAMERA] Câmera aberta no índice {index}.")
            return cap
        cap.release()
    return None


def main():
    camera = abrir_camera()
    if camera is None:
        print("Nenhuma câmera foi encontrada.")
        return

    pipeline = ReaderPipeline(
        on_result=lambda raw, final, conf: print(
            f"\n[OCR] {raw}\n[FALA] {final}\n[CONFIANÇA] {conf:.2f}"
        ),
        on_status=lambda status: print(f"[STATUS] {status}"),
    )

    print("Óculos Leitor V2 em execução. Pressione Q para sair.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                time.sleep(0.05)
                continue
            pipeline.submit_frame(frame)
            cv2.imshow("Oculos Leitor V2", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                break
    finally:
        pipeline.fechar()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
