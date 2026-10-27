# 👓 Protótipo: Óculos Leitor

Teste no PC para capturar texto via câmera USB, reconhecer usando Inteligência Artificial (RapidOCR) e converter em áudio (gTTS).

## 🛠️ Pré-requisitos
1. **Python** (3.10 ou superior).
2. **Câmera USB** (endoscópio ou webcam).
3. **Não é necessário instalar o Tesseract.** O OCR é feito 100% via IA local (RapidOCR).

## 📦 Instalação
Com o ambiente virtual ativado, instale as dependências:
    pip install -r requirements.txt

**Nota importante sobre o OpenCV:** O arquivo `requirements.txt` já fixa a versão `4.10.0.84`. Isso é essencial, pois versões mais recentes (como a 5.0.0) causam erro de interface gráfica no Windows (`cv2.error: The function is not implemented`).

## ⚙️ Configuração da Câmera
No arquivo `teste_oculos.py`, a captura está configurada para o índice `1`:
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
Se a sua câmera for a padrão do notebook, troque para `0`. Se não abrir, teste `2`.

## 🚀 Como Rodar
Execute o script:
    python teste_oculos.py

1. A janela da câmera abrirá.
2. Posicione a câmera a **4 cm** do texto (foco fixo do endoscópio).
3. Pressione **`s`** para capturar e processar.
4. O RapidOCR fará a leitura (na primeira vez, ele baixa os modelos de português).
5. O áudio será reproduzido. Pressione **Enter** no terminal após o término.
6. Pressione **`q`** para sair.

## ⚠️ Solução de Problemas
* **Erro `cv2.error: The function is not implemented`:** O OpenCV está na versão errada. Rode `pip install opencv-python==4.10.0.84`.
* **Câmera não abre:** Verifique o índice no código (`0`, `1` ou `2`).
* **Erro `'RapidOCROutput' object is not iterable`:** O código já está corrigido para a nova API do RapidOCR 3.x.
* **Texto lido errado:** A câmera tem baixa resolução (640x480). Garanta boa iluminação e mantenha a distância exata de 4 cm.