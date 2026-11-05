# 👓 Protótipo: Óculos Leitor (Tempo Real)

Sistema assistivo que captura texto em tempo real via câmera USB, reconhece o conteúdo usando Inteligência Artificial local (RapidOCR) e converte em áudio (gTTS) com feedback de voz.

## 🛠️ Pré-requisitos
1. **Python** (3.10 ou superior).
2. **Câmera USB** (endoscópio ou webcam).
3. **Não é necessário instalar o Tesseract.** O OCR é feito 100% via IA local.

## 📦 Instalação
Com o ambiente virtual ativado, instale as dependências:
    pip install -r requirements.txt

**Nota importante sobre o OpenCV:** O `requirements.txt` fixa a versão `4.10.0.84`. Versões mais recentes (como a 5.0.0) causam erro de interface gráfica no Windows (`cv2.error: The function is not implemented`).

## 🚀 Como Rodar
Execute o script:
    python oculos_v1.py

1. O programa iniciará e falará **"Procurando texto"**.
2. A janela da câmera abrirá. Posicione a câmera a aproximadamente **4 cm** do texto.
3. Mantenha a câmera firme por cerca de 2 segundos. O sistema fará a leitura em segundo plano.
4. Ao encontrar texto, ele falará **"Texto encontrado. Lendo..."** e reproduzirá o conteúdo.
5. O terminal mostrará exatamente o que a IA capturou (ex: `[IA CAPTUROU]: 'seu texto'`).
6. Se você afastar a câmera do texto, ele falará "Procurando texto" novamente.
7. Pressione **`q`** na janela da câmera para sair.

## ⚙️ Arquitetura e Otimizações
* **Multithreading:** A câmera roda a 30 FPS de forma fluida, enquanto uma thread separada processa o OCR a cada 2 segundos e outra reproduz o áudio, evitando travamentos.
* **Pré-processamento de Imagem:** O código converte a imagem para tons de cinza, aplica equalização de histograma e reduz ruído antes do OCR, melhorando a precisão em câmeras de baixa qualidade.
* **Áudio sem Cortes:** O tempo de reprodução é calculado com base na duração real do arquivo MP3 (`miniaudio.get_file_info`), evitando que a voz seja cortada no meio da frase.
* **Limpeza Automática:** Arquivos de áudio temporários usam nomes únicos (baseados em timestamp) e são limpos automaticamente para evitar conflitos de memória no Windows.

## ⚠️ Solução de Problemas
* **Erro `cv2.error: The function is not implemented`:** O OpenCV está na versão errada. Rode `pip install opencv-python==4.10.0.84`.
* **Câmera não abre:** O código já varre os índices `0`, `1` e `2` automaticamente. Se não abrir, verifique se a câmera está conectada.
* **Texto lido pela metade:** A câmera tem baixa resolução (640x480) e foco fixo. Garanta boa iluminação, evite reflexos e afaste-a um pouco (5 cm) para pegar mais área da página. O terminal `[IA CAPTUROU]` ajudará a diagnosticar.
* **Erro `'RapidOCROutput' object is not iterable`:** O código já está adaptado para a API 3.x do RapidOCR.