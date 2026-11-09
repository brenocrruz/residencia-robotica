# main_gui.py
import cv2
import threading
import time
import difflib
import customtkinter as ctk
from PIL import Image
import os
from datetime import datetime

# Importa os módulos do nosso projeto
from audio_manager import AudioManager
from ocr_engine import OCREngine
from llm_corrector import LLMCorrector
import config

# Configuração visual da Interface (Tema Escuro e moderno)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SmartGlassesApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da Janela
        self.title("Óculos Leitor Inteligente - Protótipo V1")
        self.geometry("1000x600")
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

        # Variáveis de Controle
        self.frame_atual = None
        self.lock = threading.Lock()
        self.parar_programa = False
        self.ultimo_texto_falado = ""
        self.gravando_video = False
        self.video_writer = None
        self.auto_leitura = True

        # Inicializa os Módulos (IA e Áudio)
        self.audio_manager = AudioManager()
        self.ocr_engine = OCREngine()
        self.corretor = LLMCorrector(modelo="gemma3:1b")

        # Monta a Interface
        self.setup_ui()

        # Inicia a Câmera e Threads
        self.camera = self.iniciar_camera()
        if self.camera:
            threading.Thread(target=self.thread_ocr, daemon=True).start()
            threading.Thread(target=self.audio_manager.falar, args=("Procurando texto",), daemon=True).start()
            self.atualizar_video()

    def setup_ui(self):
        # --- Painel Esquerdo (Vídeo) ---
        self.frame_esquerdo = ctk.CTkFrame(self)
        self.frame_esquerdo.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.label_video = ctk.CTkLabel(self.frame_esquerdo, text="")
        self.label_video.pack(padx=10, pady=10, expand=True)

        self.label_status = ctk.CTkLabel(
            self.frame_esquerdo, 
            text="Status: Iniciando...", 
            font=("Arial", 20, "bold"), 
            text_color="#00FF00"
        )
        self.label_status.pack(pady=10)

        # --- Painel Direito (Controles e Texto) ---
        self.frame_direito = ctk.CTkFrame(self, width=300)
        self.frame_direito.pack(side="right", fill="y", padx=10, pady=10)

        # Título
        self.label_titulo = ctk.CTkLabel(self.frame_direito, text="Controles", font=("Arial", 24, "bold"))
        self.label_titulo.pack(pady=20)

        # Botão: Ler Foto
        self.btn_foto = ctk.CTkButton(self.frame_direito, text="📸 Tirar Foto", command=self.tirar_foto, height=40)
        self.btn_foto.pack(pady=10, padx=20, fill="x")

        # Botão: Gravar Vídeo
        self.btn_gravar = ctk.CTkButton(self.frame_direito, text="🎥 Iniciar Gravação", command=self.toggle_gravacao, height=40, fg_color="#8B0000", hover_color="#FF0000")
        self.btn_gravar.pack(pady=10, padx=20, fill="x")

        # Botão: Pausar/Retomar Leitura
        self.btn_pausar = ctk.CTkButton(self.frame_direito, text="⏸️ Pausar Leitura", command=self.toggle_leitura, height=40, fg_color="#D2691E", hover_color="#FF8C00")
        self.btn_pausar.pack(pady=10, padx=20, fill="x")

        # Área de Log do Texto
        self.label_log = ctk.CTkLabel(self.frame_direito, text="Texto Capturado:", font=("Arial", 16, "bold"))
        self.label_log.pack(pady=(20, 5), padx=20, anchor="w")

        self.textbox_log = ctk.CTkTextbox(self.frame_direito, height=200, wrap="word")
        self.textbox_log.pack(pady=5, padx=20, fill="both", expand=True)
        self.textbox_log.insert("0.0", "Aguardando leitura...")
        self.textbox_log.configure(state="disabled")

    def iniciar_camera(self):
        indices = [config.CAMERA_INDEX] if config.CAMERA_INDEX is not None else [1, 2, 0]
        for i in indices:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def atualizar_video(self):
        if self.parar_programa:
            return

        sucesso, frame = self.camera.read()
        if sucesso:
            with self.lock:
                self.frame_atual = frame.copy()

            # Se estiver gravando, salva o frame no arquivo de vídeo
            if self.gravando_video and self.video_writer:
                self.video_writer.write(frame)

            # Converte o frame (BGR) para RGB para o Tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imagem_pil = Image.fromarray(frame_rgb)
            
            # Redimensiona para caber no painel
            imagem_pil = imagem_pil.resize((640, 480), Image.Resampling.LANCZOS)
            imagem_ctk = ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(640, 480))
            
            self.label_video.configure(image=imagem_ctk)

            # Atualiza o Status visual
            if self.audio_manager.falando:
                self.label_status.configure(text="Status: FALANDO", text_color="#FF0000")
            elif not self.auto_leitura:
                self.label_status.configure(text="Status: PAUSADO", text_color="#808080")
            else:
                self.label_status.configure(text="Status: PROCURANDO TEXTO", text_color="#00FF00")

        # Agenda a próxima atualização em 30ms (aprox. 30 FPS)
        self.after(30, self.atualizar_video)

    def atualizar_log(self, texto_bruto, texto_corrigido):
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("0.0", "end")
        self.textbox_log.insert("0.0", f"OCR BRUTO:\n{texto_bruto}\n\nLLM CORRIGIDO:\n{texto_corrigido}")
        self.textbox_log.configure(state="disabled")

    def thread_ocr(self):
        estado_atual = "BUSCANDO"
        
        while not self.parar_programa:
            time.sleep(config.TEMPO_ESPERA_OCR)
            
            # Não lê se estiver falando ou se a leitura estiver pausada
            if self.audio_manager.falando or not self.auto_leitura:
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
                    
                    if estado_atual == "BUSCANDO":
                        estado_atual = "LENDO"
                        texto_para_falar = "Texto encontrado. Lendo: " + texto_completo
                    else:
                        texto_para_falar = texto_completo
                        
                    threading.Thread(target=self.audio_manager.falar, args=(texto_para_falar,), daemon=True).start()
            else:
                if estado_atual == "LENDO":
                    estado_atual = "BUSCANDO"
                    threading.Thread(target=self.audio_manager.falar, args=("Procurando texto",), daemon=True).start()

    def tirar_foto(self):
        with self.lock:
            if self.frame_atual is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_foto = f"foto_{timestamp}.jpg"
                cv2.imwrite(nome_foto, self.frame_atual)
                print(f"[FOTO] Salva como {nome_foto}")
                
                # Feedback visual rápido
                self.btn_foto.configure(text="✅ Salvo!", fg_color="#006400")
                self.after(1500, lambda: self.btn_foto.configure(text="📸 Tirar Foto", fg_color=["#3B8ED0", "#1F6AA5"]))

    def toggle_gravacao(self):
        if not self.gravando_video:
            # Iniciar gravação
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_video = f"video_{timestamp}.mp4"
            
            # Pega a resolução real da câmera
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Codec de vídeo (mp4v funciona bem no Windows)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(nome_video, fourcc, 20.0, (width, height))
            
            self.gravando_video = True
            self.btn_gravar.configure(text="⏹️ Parar Gravação", fg_color="#FF0000", hover_color="#8B0000")
            print(f"[VÍDEO] Gravando em {nome_video}")
        else:
            # Parar gravação
            self.gravando_video = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            self.btn_gravar.configure(text="🎥 Iniciar Gravação", fg_color="#8B0000", hover_color="#FF0000")
            print("[VÍDEO] Gravação finalizada.")

    def toggle_leitura(self):
        self.auto_leitura = not self.auto_leitura
        if self.auto_leitura:
            self.btn_pausar.configure(text="⏸️ Pausar Leitura", fg_color="#D2691E", hover_color="#FF8C00")
        else:
            self.btn_pausar.configure(text="▶️ Retomar Leitura", fg_color="#006400", hover_color="#008000")

    def fechar_app(self):
        print("Fechando o aplicativo...")
        self.parar_programa = True
        if self.video_writer:
            self.video_writer.release()
        if self.camera:
            self.camera.release()
        self.destroy()

if __name__ == "__main__":
    app = SmartGlassesApp()
    app.mainloop()