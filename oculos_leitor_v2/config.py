"""Configurações centrais do Óculos Leitor V2."""

# Câmera
CAMERA_INDEX = None  # None: tenta câmeras USB (1, 2) e depois a integrada (0)
CAMERA_BACKEND_DSHOW = True
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# OCR
OCR_INTERVAL_SECONDS = 0.55
OCR_CONFIDENCE_MIN = 0.40
OCR_PREPROCESSING = "clahe_sharpen"  # "none", "clahe", "clahe_sharpen"
OCR_MAX_IMAGE_WIDTH = 960  # amplia apenas para OCR; não altera a câmera
MIN_TEXT_LENGTH = 5
STABILITY_SIMILARITY = 0.72
STABILITY_CONFIRMATIONS = 2
DUPLICATE_SIMILARITY = 0.88

# Correção contextual: desativada por padrão para poupar RAM e latência.
ENABLE_LLM_CORRECTION = False
LLM_MODEL = "gemma3:1b"
LLM_CONFIDENCE_TRIGGER = 0.65  # só tenta corrigir abaixo desta confiança
LLM_TIMEOUT_SECONDS = 20

# Kokoro TTS
KOKORO_MODEL_PATH = "models/kokoro-v1.0.onnx"
KOKORO_VOICES_PATH = "models/voices-v1.0.bin"
KOKORO_VOICE = "pf_dora"  # pt-BR feminina; alternativas: pm_alex, pm_santa
KOKORO_LANGUAGE = "pt-br"
KOKORO_SPEED = 1.0

# Áudio
AUDIO_QUEUE_SIZE = 2
AUDIO_SAMPLE_RATE_FALLBACK = 24000

# Interface
VIDEO_UPDATE_MS = 30
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480
