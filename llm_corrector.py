# llm_corrector.py
import ollama

class LLMCorrector:
    def __init__(self, modelo="gemma3:1b"):
        self.modelo = modelo

    def corrigir(self, texto_bruto):
        if not texto_bruto or len(texto_bruto) < 5:
            return texto_bruto

        # O prompt é a parte mais importante: ele "ensina" o LLM a tarefa
        prompt = f"""
Você é um assistente especializado em corrigir erros de OCR (reconhecimento óptico de caracteres) em português.

Abaixo está um texto extraído de uma imagem por uma câmera de baixa qualidade. Ele contém erros de leitura, letras trocadas, palavras coladas e falta de pontuação.

Sua tarefa é:
1. Corrigir as palavras erradas usando o contexto da frase.
2. Adicionar pontuação e acentuação onde estiver faltando.
3. Manter o significado original e o idioma português.
4. Retornar APENAS o texto corrigido, sem explicações ou introduções.

Texto bruto do OCR:
"{texto_bruto}"

Texto corrigido:
"""
        try:
            resposta = ollama.chat(
                model=self.modelo,
                messages=[{'role': 'user', 'content': prompt}]
            )
            texto_corrigido = resposta['message']['content'].strip()
            return texto_corrigido
        except Exception as e:
            print(f"[LLM] Erro na correção: {e}")
            return texto_bruto # Se falhar, retorna o texto original