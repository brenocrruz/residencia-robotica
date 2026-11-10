# main_gui.py
import cv2
import threading
import time
import difflib
import customtkinter as ctk
from PIL import Image

from audio_manager import AudioManager
from ocr_engine import OCREngine
from llm_corrector import LLMCorrector
import config

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SmartGlassesApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Óculos Leitor Inteligente - Apresentação")
        self.geometry("1100x650")
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

        # Variáveis de Controle
        self.frame_atual = None
        self.lock = threading.Lock()
        self.parar_programa = False
        self.ultimo_texto_falado = ""
        self.estado_atual = "BUSCANDO"
        
        # Inicializa Módulos
        print("Iniciando sistema...")
        self.audio_manager = AudioManager()
        self.ocr_engine = OCREngine()
        self.corretor = LLMCorrector(modelo="gemma3:1b")

        # Monta a Interface
        self.setup_ui()

        # Inicia a Câmera
        self.camera = self.iniciar_camera()
        
        if self.camera:
            # Thread do OCR (IA)
            threading.Thread(target=self.thread_ocr, daemon=True).start()
            # Fala a primeira mensagem
            threading.Thread(target=self.audio_manager.falar, args=("Procurando texto",), daemon=True).start()
            # Inicia o loop de vídeo
            self.atualizar_video()
        else:
            self.atualizar_status("Erro: Câmera não encontrada", "#FF0000")

    def setup_ui(self):
        # Painel Esquerdo (Vídeo)
        self.frame_esquerdo = ctk.CTkFrame(self)
        self.frame_esquerdo.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.label_video = ctk.CTkLabel(self.frame_esquerdo, text="Iniciando câmera...")
        self.label_video.pack(padx=10, pady=10, expand=True)

        self.label_status = ctk.CTkLabel(self.frame_esquerdo, text="Status: Aguardando...", font=("Arial", 20, "bold"), text_color="#FFA500")
        self.label_status.pack(pady=10)

        # Painel Direito (Logs)
        self.frame_direito = ctk.CTkFrame(self, width=350)
        self.frame_direito.pack(side="right", fill="y", padx=10, pady=10)

        self.label_titulo = ctk.CTkLabel(self.frame_direito, text="Leitura da IA", font=("Arial", 24, "bold"))
        self.label_titulo.pack(pady=20)

        self.textbox_log = ctk.CTkTextbox(self.frame_direito, height=500, wrap="word", font=("Arial", 14))
        self.textbox_log.pack(pady=5, padx=20, fill="both", expand=True)
        self.textbox_log.insert("0.0", "Aguardando leitura...")
        self.textbox_log.configure(state="disabled")

    def iniciar_camera(self):
        # Prioriza a câmera USB (1 ou 2) e deixa a do notebook (0) por último
        indices = [config.CAMERA_INDEX] if config.CAMERA_INDEX is not None else [1, 2, 0]
        for i in indices:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                print(f"Câmera conectada no índice {i}.")
                return cap
            cap.release()
        return None

    def atualizar_video(self):
        if self.parar_programa:
            return

        if self.camera:
            sucesso, frame = self.camera.read()
            if sucesso:
                with self.lock:
                    self.frame_atual = frame.copy()

                # Converte para exibir na tela
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagem_pil = Image.fromarray(frame_rgb)
                # Redimensiona para caber na interface sem distorcer
                imagem_pil = imagem_pil.resize((640, 480), Image.Resampling.LANCZOS)
                imagem_ctk = ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(640, 480))
                self.label_video.configure(image=imagem_ctk, text="")

                # Atualiza o status visual
                if self.audio_manager.falando:
                    self.atualizar_status("Status: FALANDO", "#FF0000")
                else:
                    self.atualizar_status("Status: PROCURANDO TEXTO", "#00FF00")

        # Chama a si mesmo a cada 30ms (aprox 33 FPS)
        self.after(30, self.atualizar_video)

    def atualizar_status(self, texto, cor):
        self.label_status.configure(text=texto, text_color=cor)

    def atualizar_log(self, bruto, corrigido):
        def _update():
            self.textbox_log.configure(state="normal")
            self.textbox_log.delete("0.0", "end")
            self.textbox_log.insert("0.0", f"OCR BRUTO:\n{bruto}\n\nLLM CORRIGIDO:\n{corrigido}")
            self.textbox_log.configure(state="disabled")
        self.after(0, _update)

    def thread_ocr(self):
        while not self.parar_programa:
            time.sleep(config.TEMPO_ESPERA_OCR)
            
            if self.audio_manager.falando:
                continue
                
            with self.lock:
                if self.frame_atual is None:
                    continue
                img_para_ler = self.frame_atual.copy()
            
            texto_bruto = self.ocr_engine.processar(img_para_ler)
            texto_completo = texto_bruto
            
            if len(texto_bruto) > 0:
                texto_completo = self.corretor.corrigir(texto_bruto)
                self.atualizar_log(texto_bruto, texto_completo)
            
            if len(texto_completo) > 5:
                similaridade = difflib.SequenceMatcher(None, self.ultimo_texto_falado, texto_completo).ratio()
                
                if similaridade < config.SIMILARIDADE_MINIMA: 
                    self.ultimo_texto_falado = texto_completo
                    
                    if self.estado_atual == "BUSCANDO":
                        self.estado_atual = "LENDO"
                        texto_para_falar = "Texto encontrado. Lendo: " + texto_completo
                    else:
                        texto_para_falar = texto_completo
                        
                    threading.Thread(target=self.audio_manager.falar, args=(texto_para_falar,), daemon=True).start()
            else:
                if self.estado_atual == "LENDO":
                    self.estado_atual = "BUSCANDO"
                    threading.Thread(target=self.audio_manager.falar, args=("Procurando texto",), daemon=True).start()

    def fechar_app(self):
        self.parar_programa = True
        if self.camera:
            self.camera.release()
        self.destroy()

if __name__ == "__main__":
    app = SmartGlassesApp()
    app.mainloop()