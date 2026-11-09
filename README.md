# 👓 Protótipo: Óculos Leitor Inteligente

Sistema assistivo que captura texto via câmera USB, reconhece usando Inteligência Artificial local (RapidOCR), corrige o contexto usando um Modelo de Linguagem (Ollama) e converte em áudio (gTTS).

O projeto foi modularizado e agora conta com uma **Interface Gráfica (GUI)** moderna, permitindo o uso intuitivo no computador e recursos de gravação.

## 🛠️ Pré-requisitos
1. **Python** (3.10 ou superior).
2. **Câmera USB** (endoscópio ou webcam).
3. **Ollama instalado** (para a correção contextual do texto).
    * Baixe em: [ollama.com](https://ollama.com)
    * Baixe o modelo de português rodando no terminal: `ollama pull gemma3:1b`
4. **Não é necessário instalar o Tesseract.** O OCR é feito 100% via IA local (RapidOCR).

## 📦 Instalação
Com o ambiente virtual ativado, instale as dependências:
    pip install -r requirements.txt

**Nota importante sobre o OpenCV:** O `requirements.txt` fixa a versão `4.10.0.84`. Versões mais recentes (como a 5.0.0) causam erro de interface gráfica no Windows (`cv2.error: The function is not implemented`).

## 🚀 Como Rodar
Execute o arquivo da interface gráfica:
    python main_gui.py

1. A interface abrirá dividida em duas partes (vídeo à esquerda, controles à direita).
2. O sistema iniciará falando **"Procurando texto"**.
3. Posicione a câmera a aproximadamente **4 cm** do texto (devido ao foco fixo do endoscópio).
4. O sistema fará a leitura em segundo plano (a cada 2 segundos) e falará o texto corrigido.
5. A caixa de texto na interface mostrará a diferença entre o **OCR Bruto** e o **LLM Corrigido**.
6. Utilize os botões na tela:
    * **📸 Tirar Foto:** Salva um frame em `.jpg`.
    * **🎥 Iniciar Gravação:** Salva um vídeo `.mp4` do que a câmera vê.
    * **⏸️ Pausar Leitura:** Para a leitura automática sem fechar o programa.
7. Para encerrar, feche a janela ou pressione `Ctrl+C` no terminal.

## ⚙️ Arquitetura e Otimizações
* **Modularização:** O código foi dividido em `config.py`, `audio_manager.py`, `ocr_engine.py`, `llm_corrector.py` e `main_gui.py`, facilitando a manutenção.
* **Correção com LLM:** O texto bruto do OCR (ex: erros de leitura como "oslular") é enviado ao Ollama, que usa o contexto para corrigir para "celular" antes de falar.
* **Multithreading:** A câmera roda a 30 FPS de forma fluida, enquanto o OCR e o áudio rodam em threads separadas, evitando travamentos.
* **Pré-processamento de Imagem:** Conversão para tons de cinza, equalização de histograma e redução de ruído antes do OCR, melhorando a precisão.
* **Áudio sem Cortes:** O tempo de reprodução é calculado com base na duração real do arquivo MP3 (`miniaudio.get_file_info`).
* **Prioridade de Câmera:** O sistema busca câmeras externas (índices 1 e 2) antes da webcam do notebook (índice 0).
* **Fila de Áudio Segura:** Arquivos de áudio temporários usam nomes únicos para evitar conflitos de memória (PermissionError) no Windows.

## ⚠️ Solução de Problemas
* **Erro `cv2.error: The function is not implemented`:** O OpenCV está na versão errada. Rode `pip install opencv-python==4.10.0.84`.
* **Texto lido pela metade:** A câmera tem baixa resolução e foco fixo. Garanta boa iluminação, evite reflexos e mantenha a distância exata.
* **Ollama não corrige o texto:** Verifique se o aplicativo do Ollama está aberto e rodando em segundo plano no seu computador. Se o modelo não for encontrado, rode `ollama pull gemma3:1b`.