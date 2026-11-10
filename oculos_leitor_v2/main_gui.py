"""Interface gráfica do Óculos Leitor V2."""

import queue
import threading
from datetime import datetime

import cv2
import customtkinter as ctk
from PIL import Image

import config
from reader_pipeline import ReaderPipeline


class SmartGlassesApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Óculos Leitor Inteligente — V2")
        self.geometry("1050x680")
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

        self.parar = False
        self.camera = None
        self.pipeline = None
        self.frame_atual = None
        self.gravando = False
        self.video_writer = None
        self.ui_queue = queue.Queue()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._montar_interface()
        self.camera = self._abrir_camera()

        if self.camera is None:
            self.label_status.configure(text="Não foi possível abrir a câmera.", text_color="#ff5555")
            return

        # O carregamento do RapidOCR ocorre aqui; o Kokoro carrega em sua própria thread.
        self.pipeline = ReaderPipeline(
            on_result=self._resultado_thread,
            on_status=self._status_thread,
        )
        self.after(config.VIDEO_UPDATE_MS, self._atualizar_video)
        self.after(100, self._processar_fila_ui)

    def _montar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        right = ctk.CTkFrame(self, width=320)
        right.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="nsew")

        self.label_video = ctk.CTkLabel(left, text="Inicializando câmera...")
        self.label_video.pack(expand=True, fill="both", padx=10, pady=10)

        self.label_status = ctk.CTkLabel(left, text="Status: inicializando", font=("Arial", 18, "bold"))
        self.label_status.pack(pady=10)

        ctk.CTkLabel(right, text="Controles", font=("Arial", 24, "bold")).pack(pady=(20, 12))
        self.btn_pause = ctk.CTkButton(right, text="Pausar leitura", command=self.toggle_leitura)
        self.btn_pause.pack(fill="x", padx=18, pady=7)
        self.btn_photo = ctk.CTkButton(right, text="Tirar foto", command=self.tirar_foto)
        self.btn_photo.pack(fill="x", padx=18, pady=7)
        self.btn_record = ctk.CTkButton(right, text="Iniciar gravação", command=self.toggle_gravacao)
        self.btn_record.pack(fill="x", padx=18, pady=7)

        ctk.CTkLabel(right, text="Texto reconhecido", font=("Arial", 16, "bold")).pack(
            anchor="w", padx=18, pady=(22, 5)
        )
        self.textbox = ctk.CTkTextbox(right, width=290, height=260, wrap="word")
        self.textbox.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        self.textbox.insert("1.0", "Aguardando texto...")
        self.textbox.configure(state="disabled")

    def _abrir_camera(self):
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

    def _resultado_thread(self, raw, final, confidence):
        self.ui_queue.put(("result", raw, final, confidence))

    def _status_thread(self, status):
        self.ui_queue.put(("status", status))

    def _processar_fila_ui(self):
        if self.parar:
            return
        try:
            while True:
                item = self.ui_queue.get_nowait()
                if item[0] == "status":
                    self.label_status.configure(text=f"Status: {item[1]}")
                elif item[0] == "result":
                    _, raw, final, confidence = item
                    self.textbox.configure(state="normal")
                    self.textbox.delete("1.0", "end")
                    self.textbox.insert(
                        "1.0",
                        f"OCR bruto:\n{raw}\n\nTexto enviado à fala:\n{final}\n\n"
                        f"Confiança média do OCR: {confidence:.2f}",
                    )
                    self.textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._processar_fila_ui)

    def _atualizar_video(self):
        if self.parar:
            return
        if self.camera:
            ok, frame = self.camera.read()
            if ok:
                self.frame_atual = frame
                if self.pipeline:
                    self.pipeline.submit_frame(frame)

                if self.gravando and self.video_writer:
                    self.video_writer.write(frame)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb).resize(
                    (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
                    Image.Resampling.BILINEAR,
                )
                self._photo = ctk.CTkImage(light_image=image, dark_image=image,
                                           size=(config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))
                self.label_video.configure(image=self._photo, text="")
        self.after(config.VIDEO_UPDATE_MS, self._atualizar_video)

    def toggle_leitura(self):
        if not self.pipeline:
            return
        enabled = not self.pipeline._enabled
        self.pipeline.set_enabled(enabled)
        self.btn_pause.configure(text="Pausar leitura" if enabled else "Retomar leitura")

    def tirar_foto(self):
        if self.frame_atual is None:
            return
        filename = datetime.now().strftime("foto_%Y%m%d_%H%M%S.jpg")
        cv2.imwrite(filename, self.frame_atual)
        self.label_status.configure(text=f"Foto salva: {filename}")

    def toggle_gravacao(self):
        if not self.camera:
            return
        if not self.gravando:
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or config.CAMERA_WIDTH
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or config.CAMERA_HEIGHT
            filename = datetime.now().strftime("video_%Y%m%d_%H%M%S.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
            if not self.video_writer.isOpened():
                self.video_writer = None
                self.label_status.configure(text="Não foi possível iniciar a gravação.")
                return
            self.gravando = True
            self.btn_record.configure(text="Parar gravação")
            self.label_status.configure(text=f"Gravando: {filename}")
        else:
            self.gravando = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.btn_record.configure(text="Iniciar gravação")
            self.label_status.configure(text="Gravação finalizada.")

    def fechar_app(self):
        self.parar = True
        if self.pipeline:
            self.pipeline.fechar()
        if self.video_writer:
            self.video_writer.release()
        if self.camera:
            self.camera.release()
        self.destroy()


if __name__ == "__main__":
    app = SmartGlassesApp()
    app.mainloop()
