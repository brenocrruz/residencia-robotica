# ocr_engine.py
import cv2
from rapidocr import RapidOCR
import config

class OCREngine:
    def __init__(self):
        print("Carregando modelo RapidOCR (IA local)...")
        self.ocr = RapidOCR(params={"Rec.lang_type": "pt"})
        print("Modelo carregado com sucesso!")

    def _melhorar_imagem(self, img):
        """Aumenta o contraste e reduz ruído."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        eq = cv2.equalizeHist(gray)
        blur = cv2.GaussianBlur(eq, (3, 3), 0)
        return blur

    def processar(self, img):
        """Recebe a imagem, pré-processa e retorna o texto."""
        try:
            img_processada = self._melhorar_imagem(img)
            resultado = self.ocr(img_processada)
            textos = []
            
            if resultado and resultado.txts is not None:
                for texto, score in zip(resultado.txts, resultado.scores):
                    if score > config.CONFIANCA_MINIMA:
                        textos.append(texto)
            
            return " ".join(textos).strip()
        except Exception as e:
            print(f"Erro no OCR: {e}")
            return ""