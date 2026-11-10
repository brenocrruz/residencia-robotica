"""Coordena frames, OCR, validação, correção opcional e fila de áudio."""

import difflib
import threading
import time
import re

import config
from ocr_engine import OCREngine
from llm_corrector import LLMCorrector
from audio_manager import AudioManager


def normalizar(texto):
    texto = (texto or "").lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


class ReaderPipeline:
    def __init__(self, on_result=None, on_status=None):
        self.on_result = on_result
        self.on_status = on_status
        self.ocr = OCREngine()
        self.corrector = LLMCorrector()
        self.audio = AudioManager(on_status=self._status)
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._stop = threading.Event()
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._last_spoken = ""
        self._candidate = ""
        self._candidate_count = 0
        self._first_detection = True
        self._thread.start()

    def _status(self, message):
        if self.on_status:
            self.on_status(message)

    def submit_frame(self, frame):
        if frame is None:
            return
        with self._frame_lock:
            self._latest_frame = frame.copy()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self._status("Leitura ativa" if enabled else "Leitura pausada")

    def _emit_result(self, raw, final, confidence):
        if self.on_result:
            self.on_result(raw, final, confidence)

    def _loop(self):
        next_cycle = time.perf_counter()
        while not self._stop.is_set():
            # Mantém o intervalo como alvo entre inícios de ciclos, não como
            # uma pausa adicional somada ao tempo gasto pelo OCR.
            delay = next_cycle - time.perf_counter()
            if delay > 0 and self._stop.wait(delay):
                break
            next_cycle += config.OCR_INTERVAL_SECONDS

            if not self._enabled:
                continue

            with self._frame_lock:
                frame = None if self._latest_frame is None else self._latest_frame.copy()

            if frame is None:
                continue

            started = time.perf_counter()
            raw_text, confidence = self.ocr.processar(frame)
            raw_text = (raw_text or "").strip()

            if len(raw_text) < config.MIN_TEXT_LENGTH:
                self._candidate = ""
                self._candidate_count = 0
                continue

            candidate_norm = normalizar(raw_text)
            previous_norm = normalizar(self._candidate)
            similarity = difflib.SequenceMatcher(None, previous_norm, candidate_norm).ratio() if previous_norm else 0.0

            if previous_norm and similarity >= config.STABILITY_SIMILARITY:
                self._candidate_count += 1
            else:
                self._candidate = raw_text
                self._candidate_count = 1

            if self._candidate_count < config.STABILITY_CONFIRMATIONS:
                continue

            # Atualiza o candidato com a leitura mais recente, sem aguardar LLM.
            self._candidate = raw_text
            final_text = raw_text

            if config.ENABLE_LLM_CORRECTION and confidence < config.LLM_CONFIDENCE_TRIGGER:
                final_text = self.corrector.corrigir(raw_text)

            final_norm = normalizar(final_text)
            last_norm = normalizar(self._last_spoken)
            duplicate_similarity = (
                difflib.SequenceMatcher(None, last_norm, final_norm).ratio()
                if last_norm else 0.0
            )

            if duplicate_similarity >= config.DUPLICATE_SIMILARITY:
                continue

            self._last_spoken = final_text
            self._emit_result(raw_text, final_text, confidence)

            if self._first_detection:
                self.audio.falar("Texto encontrado. " + final_text)
                self._first_detection = False
            else:
                self.audio.falar(final_text)

            duration = time.perf_counter() - started
            print(f"[PIPELINE] OCR + validação: {duration:.2f}s | confiança: {confidence:.2f}")

            # Se o OCR levou mais que o intervalo-alvo, não acumula ciclos
            # atrasados: começa uma nova tentativa com o frame mais recente.
            if next_cycle < time.perf_counter():
                next_cycle = time.perf_counter()

    def fechar(self):
        self._stop.set()
        self.audio.fechar()
