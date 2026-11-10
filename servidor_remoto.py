# servidor_remoto.py
import socket
import struct
import threading
import time
import difflib
import cv2
import numpy as np
import os

from ocr_engine import OCREngine
from llm_corrector import LLMCorrector
import config

# Configurações de Rede
HOST = '0.0.0.0'  
PORT = 5000

print("Carregando modelos de IA...")
ocr_engine = OCREngine()
corretor = LLMCorrector(modelo="gemma3:1b")
print(f"Servidor pronto! Escutando na porta {PORT}")

def receber_exato(conn, tamanho):
    dados = b''
    while len(dados) < tamanho:
        pacote = conn.recv(tamanho - len(dados))
        if not pacote:
            return None
        dados += pacote
    return dados

def processar_cliente(conn, addr):
    print(f"\n[Rede] Raspberry Pi conectado: {addr}")
    estado_atual = "BUSCANDO"
    ultimo_texto_falado = ""

    try:
        while True:
            tamanho_bytes = receber_exato(conn, 8)
            if not tamanho_bytes:
                break
            tamanho = struct.unpack("Q", tamanho_bytes)[0]

            imagem_bytes = receber_exato(conn, tamanho)
            if not imagem_bytes:
                break

            np_arr = np.frombuffer(imagem_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            texto_bruto = ocr_engine.processar(frame)
            texto_completo = texto_bruto

            if len(texto_bruto) > 0:
                texto_completo = corretor.corrigir(texto_bruto)
                print(f"[OCR]: '{texto_bruto}'")
                print(f"[LLM]: '{texto_completo}'")

            texto_para_enviar = ""
            if len(texto_completo) > 5:
                similaridade = difflib.SequenceMatcher(None, ultimo_texto_falado, texto_completo).ratio()
                if similaridade < config.SIMILARIDADE_MINIMA:
                    ultimo_texto_falado = texto_completo
                    if estado_atual == "BUSCANDO":
                        estado_atual = "LENDO"
                        texto_para_enviar = "Texto encontrado. Lendo: " + texto_completo
                    else:
                        texto_para_enviar = texto_completo
            else:
                if estado_atual == "LENDO":
                    estado_atual = "BUSCANDO"
                    texto_para_enviar = "Procurando texto"

            resposta = texto_para_enviar.encode('utf-8')
            conn.sendall(struct.pack("Q", len(resposta)) + resposta)

    except ConnectionResetError:
        print(f"[Rede] Pi desconectado.")
    finally:
        conn.close()

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(1)

    while True:
        conn, addr = servidor.accept()
        threading.Thread(target=processar_cliente, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    iniciar_servidor()