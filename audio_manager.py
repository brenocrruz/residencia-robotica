# audio_manager.py
import miniaudio
import os
import time
import glob
from gtts import gTTS
import config

class AudioManager:
    def __init__(self):
        self.falando = False
        self.limpar_audios_antigos()

    def limpar_audios_antigos(self):
        for f in glob.glob("audio_*.mp3"):
            try: os.remove(f)
            except: pass

    def falar(self, texto):
        if self.falando or not texto:
            return
        
        self.falando = True
        nome_arquivo = f"audio_{int(time.time() * 1000)}.mp3"
        
        try:
            print(f"\n[AUDIO] Falando: '{texto[:60]}...'")
            tts = gTTS(text=texto, lang=config.LANG, tld=config.TLD, slow=False)
            tts.save(nome_arquivo)

            # Obtém a duração exata para não cortar o áudio
            info = miniaudio.get_file_info(nome_arquivo)
            duracao = info.duration

            stream = miniaudio.stream_file(nome_arquivo)
            with miniaudio.PlaybackDevice() as device:
                device.start(stream)
                time.sleep(duracao + 0.2)
                
        except Exception as e:
            print(f"Erro no áudio: {e}")
        finally:
            self.falando = False
            try:
                if os.path.exists(nome_arquivo):
                    os.remove(nome_arquivo)
            except PermissionError:
                pass