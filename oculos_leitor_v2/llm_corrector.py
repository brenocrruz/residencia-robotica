"""Correção contextual opcional via Ollama. Desativada por padrão."""

import config


class LLMCorrector:
    def __init__(self, model=None):
        self.model = model or config.LLM_MODEL
        self._ollama = None

    def _get_client(self):
        if self._ollama is None:
            import ollama
            self._ollama = ollama
        return self._ollama

    def corrigir(self, texto_bruto):
        if not config.ENABLE_LLM_CORRECTION:
            return texto_bruto
        if not texto_bruto or len(texto_bruto.strip()) < config.MIN_TEXT_LENGTH:
            return texto_bruto

        prompt = (
            "Corrija somente erros evidentes de reconhecimento óptico de caracteres "
            "em português brasileiro. Preserve nomes, números, pontuação e o sentido. "
            "Não invente palavras nem complete trechos ausentes. Retorne apenas o texto corrigido.\n\n"
            f"Texto reconhecido: {texto_bruto}"
        )

        try:
            client = self._get_client()
            response = client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0, "num_predict": 160},
            )
            corrected = response["message"]["content"].strip()
            return corrected or texto_bruto
        except Exception as exc:
            print(f"[LLM] Correção indisponível; usando OCR bruto: {exc}")
            return texto_bruto
