# 👓 Protótipo: Óculos Leitor

Teste no PC para capturar texto via câmera USB, reconhecer (OCR) e converter em áudio (TTS).

## 🛠️ Pré-requisitos
1. **Python** (3.10+).
2. **Tesseract OCR** instalado (marque a opção "Additional language data" para **Português**).

## 📦 Instalação
Com o ambiente virtual ativado, instale as dependências:
    pip install -r requirements.txt

## ⚙️ Configuração
Abra o arquivo `teste_oculos.py` e verifique se o caminho do Tesseract está correto para a sua máquina (linha `caminho_tesseract`):
    caminho_tesseract = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

## 🚀 Como Rodar
Execute o script:
    python teste_oculos.py

1. A janela da câmera abrirá.
2. Posicione a câmera a **4 cm** do texto.
3. Pressione **`s`** para capturar e processar.
4. Pressione **`q`** para sair.

## ⚠️ Solução de Problemas
* **Câmera não abre:** O código já usa `cv2.CAP_DSHOW` para corrigir erros de USB no Windows.
* **Áudio não toca:** Verifique o volume do sistema. O áudio é reproduzido pelo player nativo do Windows.
* **Texto lido errado:** A câmera tem baixa resolução (640x480). Garanta boa iluminação e mantenha a distância exata de 4 cm.