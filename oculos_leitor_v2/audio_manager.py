"""Fila de fala com Kokoro ONNX, carregado uma única vez em segundo plano."""

import queue
import threading
import time
import numpy as np
import config


class AudioManager:
    def __init__(self, on_status=None):
        self._queue = queue.Queue(maxsize=config.AUDIO_QUEUE_SIZE)
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._speaking = False
        self._ready = False
        self._error = None
        self._on_status = on_status
        self._kokoro = None
        self._sounddevice = None
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    @property
    def falando(self):
        with self._state_lock:
            return self._speaking

    @property
    def pronto(self):
        with self._state_lock:
            return self._ready

    @property
    def erro(self):
        return self._error

    def _set_status(self, message):
        if self._on_status:
            try:
                self._on_status(message)
            except Exception:
                pass

    def falar(self, texto):
        texto = (texto or "").strip()
        if not texto or self._stop_event.is_set():
            return False

        # Não deixa a fila crescer com frases antigas. Se estiver cheia, descarta
        # a frase pendente mais antiga (a fala que já começou não é interrompida).
        try:
            self._queue.put_nowait(texto)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(texto)
            except queue.Full:
                return False
        return True

    def _initialize(self):
        import os
        from kokoro_onnx import Kokoro, EspeakConfig
        import sounddevice as sd

        # Pasta oficial, limpa e sem restrições
        espeak_path = "C:\\Users\\Public\\espeak-ng-data"

        if not os.path.exists(espeak_path):
            raise FileNotFoundError(
                f"A pasta '{espeak_path}' não foi encontrada! "
                "Certifique-se de copiar a pasta 'espeak-ng-data' do eSpeak NG instalado para este caminho."
            )

        # Configura as variáveis internas do Kokoro
        os.environ["ESPEAK_DATA_PATH"] = espeak_path
        cfg = EspeakConfig(data_path=espeak_path)

        model_path = config.KOKORO_MODEL_PATH
        voices_path = config.KOKORO_VOICES_PATH
        
        self._kokoro = Kokoro(
            model_path,
            voices_path,
            espeak_config=cfg
        )

        # Diagnóstico das entradas esperadas pelo modelo ONNX
        session = getattr(self._kokoro, "sess", None)

        if session is not None:
            print("\n[ONNX] Entradas do modelo Kokoro:")

            for entrada in session.get_inputs():
                print(
                    f"Nome: {entrada.name} | "
                    f"Tipo: {entrada.type} | "
                    f"Formato: {entrada.shape}"
                )
        self._sounddevice = sd
        
        # 🚀 TESTE DE SOM: Toca um bipe rápido para provar que o canal de áudio funciona
        fs = 44100
        t = np.linspace(0, 0.3, int(fs * 0.3), endpoint=False)
        beep = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        sd.play(beep, fs)
        sd.wait()
        
        with self._state_lock:
            self._ready = True
        self._set_status("Áudio pronto")

    def _worker_loop(self):
        try:
            self._set_status("Carregando Kokoro...")
            self._initialize()
        except Exception as exc:
            self._error = str(exc)
            self._set_status(f"Falha ao carregar Kokoro: {exc}")
            print(f"[AUDIO] Não foi possível inicializar Kokoro: {exc}")
            return

        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                with self._state_lock:
                    self._speaking = True

                started = time.perf_counter()
                
                # Remove quebras de linha e limpa o texto capturado do OCR
                clean_text = " ".join(text.split()).strip()
                if not clean_text:
                    continue

                # 🚀 O REMENDO DO ONNX V1.0: Tentamos gerar com velocidade normal.
                # Se o modelo reclamar de tipo (int32 vs float), convertemos na marra.
                samples, sample_rate = self._kokoro.create(
                    clean_text,
                    voice=config.KOKORO_VOICE,
                    speed=float(config.KOKORO_SPEED),
                    lang=config.KOKORO_LANGUAGE,
                )
                
                # Garante que o array está pronto para a placa de som
                samples = np.ascontiguousarray(samples, dtype=np.float32)

                if samples.size > 0:
                    # Envia em Mono com a taxa de amostragem oficial do modelo
                    self._sounddevice.play(samples, samplerate=int(sample_rate), blocking=True)
                    self._sounddevice.wait()
                else:
                    print("[AUDIO] O Kokoro gerou um áudio vazio para este texto.")

                elapsed = time.perf_counter() - started
                print(f"[AUDIO] Fala concluída em {elapsed:.2f}s: {clean_text[:70]}")
            except Exception as exc:
                print(f"[AUDIO] Erro ao gerar/reproduzir fala: {exc}")
            finally:
                with self._state_lock:
                    self._speaking = False
                self._queue.task_done()


    def fechar(self):
        self._stop_event.set()
        try:
            if self._sounddevice:
                self._sounddevice.stop()
        except Exception:
            pass
