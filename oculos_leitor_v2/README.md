# 👓 Óculos Leitor Inteligente — V2

Sistema assistivo que captura texto por uma câmera USB (endoscópio), reconhece caracteres com RapidOCR e converte o resultado em fala usando Kokoro TTS local via ONNX Runtime.

A V2 reorganiza o fluxo para que a captura continue enquanto o OCR e a reprodução de áudio acontecem em segundo plano. O sistema usa uma fila curta de áudio para evitar acumular frases antigas.

## Hardware considerado

- Intel Core i5 de 12ª geração
- 8 GB de RAM
- Câmera endoscópica USB fixa em 640 × 480
- Windows 10/11 64 bits (configuração documentada)

A resolução física da câmera não é alterada. O OCR pode ampliar a imagem internamente, mas isso não recupera detalhes que o sensor não capturou.

## O que mudou na V2

- Captura de frames independente da fala.
- OCR em intervalo configurável, sempre usando o frame mais recente.
- Pré-processamento com CLAHE e sharpening leve, sem blur agressivo como padrão.
- Confirmação de estabilidade do texto para reduzir leituras causadas por OCR instável.
- Kokoro TTS local, inicializado uma vez em thread própria.
- Fila de áudio limitada para não acumular mensagens antigas.
- Gemma/Ollama desativado por padrão; pode ser habilitado para correção seletiva.
- Atualização da interface gráfica por fila, sem manipular widgets Tkinter a partir da thread de OCR.

## Estrutura do projeto

```text
oculos-leitor/
├── audio_manager.py
├── config.py
├── llm_corrector.py
├── main.py
├── main_gui.py
├── ocr_engine.py
├── reader_pipeline.py
├── requirements.txt
└── models/
    ├── kokoro-v1.0.onnx
    └── voices-v1.0.bin
```

## 1. Instalar Python

Instale Python 3.11 ou 3.12 de 64 bits. Durante a instalação no Windows, marque **Add Python to PATH**.

Confira:

```powershell
python --version
```

## 2. Criar e ativar o ambiente virtual

No terminal, dentro da pasta do projeto:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

Se o PowerShell bloquear a ativação, use o Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

## 3. Instalar as dependências

```powershell
pip install -r requirements.txt
```

O pacote `kokoro-onnx` usa ONNX Runtime. O `sounddevice` reproduz o áudio gerado diretamente, sem precisar criar um MP3 para cada frase.

## 4. Baixar os arquivos do Kokoro

Crie a pasta de modelos:

```powershell
mkdir models
```

Baixe o modelo ONNX e o arquivo de vozes da publicação do projeto kokoro-onnx:

```powershell
Invoke-WebRequest `
  -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx" `
  -OutFile "models/kokoro-v1.0.onnx"

Invoke-WebRequest `
  -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin" `
  -OutFile "models/voices-v1.0.bin"
```

O modelo de referência é a versão ONNX padrão publicada pelo projeto. Não force uma variante INT8/quantizada sem testar antes a compatibilidade e a qualidade da voz pt-BR no seu ambiente.

## 5. Configurar a voz

Abra `config.py`.

Configuração inicial:

```python
KOKORO_VOICE = "pf_dora"
KOKORO_LANGUAGE = "pt-br"
KOKORO_SPEED = 1.0
```

Vozes brasileiras disponíveis no conjunto de vozes Kokoro:

- `pf_dora` — feminina
- `pm_alex` — masculina
- `pm_santa` — masculina

Se o áudio não iniciar, confira se os dois arquivos do modelo estão exatamente nos caminhos indicados em `config.py`.

## 6. Executar o projeto

Interface gráfica:

```powershell
python main_gui.py
```

Modo de terminal:

```powershell
python main.py
```

Na interface, use os botões para pausar a leitura, tirar fotos e gravar vídeos.

## 7. Configuração do OCR

As configurações ficam em `config.py`:

```python
OCR_INTERVAL_SECONDS = 0.55
OCR_CONFIDENCE_MIN = 0.40
OCR_PREPROCESSING = "clahe_sharpen"
OCR_MAX_IMAGE_WIDTH = 960
STABILITY_CONFIRMATIONS = 2
```

Ajuste uma variável por vez e compare a leitura com imagens reais da câmera.

Opções de pré-processamento:

- `none`: imagem em escala de cinza, sem realce.
- `clahe`: contraste local.
- `clahe_sharpen`: CLAHE com sharpening leve (padrão inicial).

A ampliação é aplicada apenas à imagem enviada ao OCR. Ela não aumenta a resolução real da câmera.

## 8. Correção opcional com Gemma/Ollama

Por padrão, a correção contextual está desativada para reduzir latência e consumo de memória.

Para habilitar:

1. Instale o Ollama: https://ollama.com
2. Baixe o modelo:

```powershell
ollama pull gemma3:1b
```

3. Em `config.py`, altere:

```python
ENABLE_LLM_CORRECTION = True
```

A correção só será chamada quando a confiança média do OCR estiver abaixo de `LLM_CONFIDENCE_TRIGGER`. Em um computador com 8 GB de RAM, monitore o consumo antes de manter Ollama e Kokoro ativos ao mesmo tempo. Se houver lentidão ou falta de memória, mantenha a correção desativada.

## 9. Teste de desempenho

Faça três testes separados:

1. OCR sem fala: observe o tempo `[PIPELINE] OCR + validação`.
2. Fala Kokoro: observe o tempo `[AUDIO] Fala concluída`.
3. Fluxo completo: confira se a câmera continua atualizando enquanto a voz é reproduzida.

Use o Gerenciador de Tarefas para observar CPU e memória. Registre os resultados antes e depois de alterar configurações.

## Solução de problemas

### Erro ao abrir a câmera
- Feche outros programas que estejam usando a câmera.
- Confira `CAMERA_INDEX` em `config.py`.
- Teste os índices 0, 1 e 2.

### Kokoro não inicializa
- Confirme que `models/kokoro-v1.0.onnx` e `models/voices-v1.0.bin` existem.
- Reinstale as dependências no ambiente virtual.
- Confira a mensagem `[AUDIO]` no terminal.

### Erro de dispositivo de áudio
- Confira se o Windows reconhece uma saída de áudio.
- Teste `sounddevice` no mesmo ambiente virtual.
- Feche aplicativos que possam estar bloqueando o dispositivo.

### OCR erra ou não encontra letras
- Melhore a iluminação e evite reflexos.
- Teste `OCR_PREPROCESSING = "clahe"` e depois `"none"`.
- Ajuste o foco/distância física do endoscópio.
- Lembre que ampliar a imagem não recupera informação que não foi capturada.

### Interface do OpenCV não abre
O projeto fixa `opencv-python==4.10.0.84` como ponto de partida para evitar incompatibilidades já observadas no ambiente Windows deste projeto. Evite instalar simultaneamente `opencv-python-headless`.

## Observações

- O sistema é um protótipo de assistência à leitura. Não deve ser usado como único meio para interpretar documentos críticos, prescrições ou informações de segurança.
- O desempenho depende da iluminação, foco, qualidade óptica, CPU e memória disponível.
- O primeiro carregamento do Kokoro é mais demorado; o modelo permanece carregado durante a execução.
- As versões e dependências podem mudar. Se uma instalação falhar, registre a mensagem completa do terminal antes de atualizar pacotes aleatoriamente.

## Referências técnicas

- Kokoro ONNX: https://github.com/thewh1teagle/kokoro-onnx
- Kokoro ONNX no PyPI: https://pypi.org/project/kokoro-onnx/
- RapidOCR: https://github.com/RapidAI/RapidOCR
- Ollama: https://ollama.com
