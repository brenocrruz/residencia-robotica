
import csv
import os
import time
import threading
from datetime import datetime


class PerformanceMonitor:
    def __init__(self, filename="desempenho.csv"):
        self.filename = filename
        self.lock = threading.Lock()
        self.cycles = {}
        
        if not os.path.exists(filename):
            with open(filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "leitura",
                    "horario",
                    "ocr_ms",
                    "espera_fala_ms",
                    "geracao_audio_ms",
                    "duracao_audio_ms",
                    "tempo_total_ms"
                ])

    def start_cycle(self):
        with self.lock:
            cycle_id = time.perf_counter()
            self.cycles[cycle_id] = {
                "inicio": cycle_id
            }
            return cycle_id

    def mark(self, cycle_id, event):
        with self.lock:
            if cycle_id in self.cycles:
                self.cycles[cycle_id][event] = time.perf_counter()

    def finish_cycle(self, cycle_id):
        with self.lock:
            data = self.cycles.pop(cycle_id, None)

        if not data:
            return

        def elapsed(start, end):
            if start not in data or end not in data:
                return None
            return round((data[end] - data[start]) * 1000, 2)

        result = [
            cycle_id,
            datetime.now().strftime("%H:%M:%S"),
            elapsed("ocr_inicio", "ocr_fim"),
            elapsed("ocr_fim", "fala_inicio"),
            elapsed("tts_inicio", "tts_fim"),
            elapsed("fala_inicio", "fala_fim"),
            round((time.perf_counter() - data["inicio"]) * 1000, 2)
        ]

        with open(self.filename, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(result)

        print(
            f"[DESEMPENHO] OCR: {result[2]} ms | "
            f"Espera até fala: {result[3]} ms | "
            f"Geração: {result[4]} ms | "
            f"Áudio: {result[5]} ms"
        )
