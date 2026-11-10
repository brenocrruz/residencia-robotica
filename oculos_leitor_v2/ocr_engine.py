"""Reconhecimento de texto com RapidOCR e pré-processamento conservador."""

import cv2
import numpy as np
from rapidocr import RapidOCR
import config


class OCREngine:
    def __init__(self):
        print("[OCR] Inicializando RapidOCR...")
        self.ocr = RapidOCR(params={"Rec.lang_type": "pt"})
        print("[OCR] RapidOCR pronto.")

    def _preprocessar(self, frame):
        if frame is None or frame.size == 0:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mode = config.OCR_PREPROCESSING

        if mode == "none":
            return gray

        # CLAHE melhora contraste local sem equalizar toda a imagem de forma agressiva.
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        if mode == "clahe":
            return enhanced

        if mode == "clahe_sharpen":
            # Unsharp masking leve. Evita o desfoque gaussiano aplicado no protótipo anterior.
            softened = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
            sharpened = cv2.addWeighted(enhanced, 1.35, softened, -0.35, 0)
            return np.clip(sharpened, 0, 255).astype(np.uint8)

        return enhanced

    def processar(self, frame):
        """Retorna (texto, confiança_média). Em caso de falha, retorna ('', 0.0)."""
        try:
            image = self._preprocessar(frame)
            if image is None:
                return "", 0.0

            # Ampliação moderada ajuda caracteres pequenos; não cria detalhe inexistente.
            height, width = image.shape[:2]
            if width < config.OCR_MAX_IMAGE_WIDTH:
                scale = config.OCR_MAX_IMAGE_WIDTH / float(width)
                new_size = (config.OCR_MAX_IMAGE_WIDTH, max(1, int(height * scale)))
                image = cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)

            result = self.ocr(image)
            if not result or result.txts is None:
                return "", 0.0

            accepted = []
            scores = []
            for text, score in zip(result.txts, result.scores):
                if not text:
                    continue
                score = float(score)
                if score >= config.OCR_CONFIDENCE_MIN:
                    accepted.append(str(text).strip())
                    scores.append(score)

            if not accepted:
                return "", 0.0

            confidence = sum(scores) / len(scores)
            return " ".join(accepted).strip(), confidence

        except Exception as exc:
            print(f"[OCR] Erro no reconhecimento: {exc}")
            return "", 0.0
