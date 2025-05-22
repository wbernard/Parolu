#!/usr/bin/env python3

import os
import subprocess
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
# GStreamer initialisieren (einmalig beim Programmstart!)
Gst.init(None)
import array
import time
import pyttsx4
import piper
from gtts import gTTS, lang
import math
import tempfile
import io
import wave
import struct
import numpy as np
import shutil
from pathlib import Path
from .pipervoice import VoiceManager
from .vocx import convert_text

class Reader():
      # Konstruktor, initialisiert Eingabewerte
    def __init__(self, text, engine, lang_code, selected_voice, pitch, speed):
        self.text = text
        self.engine = engine
        self.lang_code = lang_code  # de, it, eo, en
        self.pitch = pitch
        self.speed = speed
        self.selected_voice = selected_voice
        Gst.init(None)
        self._init_gstreamer()
        print ('in reader erhaltener lang_code  ', self.lang_code)

        self.voicemanager = VoiceManager(self)

        if self.lang_code == 'eo':
            text = convert_text(text)
            print(text)  # Ausgabe konveertiert

        if self.engine == 'pyttsx4':
            self.use_pyttsx4(text, lang_code, pitch, speed)

        elif self.engine == 'piper':
            self.use_piper(text, lang_code, selected_voice, pitch, speed)

        elif self.engine == 'gTTS':
            # Ausgabe der Audiodatei mit gTTS
            if lang_code == "de" or "it" or "es" or "fr":
                self.use_gTTS(text, lang_code)

            else:
                print ('andere Sprache funktioniert noch nicht')
                #return

        else:
            print ('andere engine funktioniert noch nicht')
            #return

    def _init_gstreamer(self):
        """Initialisiert GStreamer Pipeline"""
        self.pipeline = Gst.Pipeline.new("audio-pipeline")
        self.src = Gst.ElementFactory.make("appsrc", "source")
        convert = Gst.ElementFactory.make("audioconvert", "converter")
        sink = Gst.ElementFactory.make("autoaudiosink", "sink")

        # Pipeline aufbauen
        for element in [self.src, convert, sink]:
            self.pipeline.add(element)
        self.src.link(convert)
        convert.link(sink)

    def get_voice_path(self, lang_code: str, voice_name: str) -> tuple[str, str]:
        """Sucht nach Stimmen in Nutzerdaten oder Flatpak-Pfad."""
        # Pfade in Prioritätsreihenfolge
        search_paths = [
            # Nutzerverzeichnis (z. B. ~/.var/app/.../models/de_DE-kerstin-low.onnx)
            Path.home() / ".var" / "app" / "im.bernard.Parolu" / "data" / "parolu" / "models",
            # Flatpak-Systempfad
            Path("/app/share/piper")
        ]
        print ('voice_name  = ', voice_name)
        for base_path in search_paths:
            model_path = base_path / lang_code / f"{voice_name}/{voice_name}.onnx"
            config_path = base_path / lang_code / f"{voice_name}/{voice_name}.onnx.json"
            print ('Pfade ', model_path, config_path)
            if model_path.exists() and config_path.exists():
                return str(model_path), str(config_path)

        raise FileNotFoundError(f"Stimme {voice_name} ({lang_code}) nicht gefunden")

    def use_piper(self, text, lang_code, selected_voice, pitch, speed):  # Ausgabe über wav
        print(f"Starte Piper-Synthese für: '{text[:20]}...'")

        voices = self.voicemanager.get_installed_voices(lang_code)
        for voice in voices:
            if voice['name'] == self.selected_voice:
                voice_id = voice['id']
        try:
            # Modellpfade
            # model_path = "/app/share/piper/de/de_DE-kerstin-low.onnx"
            # config_path = "/app/share/piper/de/de_DE-kerstin-low.onnx.json"

            #model_path, config_path = self.get_voice_path(lang_code, "de_DE-kerstin-low")
            model_path, config_path = self.get_voice_path(lang_code, voice_id)
            print(f"Verwende Modell: {model_path}")

            if not (os.path.exists(model_path) and os.path.exists(config_path)):
                print("❌ Modell oder Konfiguration fehlen")
                return

            print(f"Starte Synthese mit: {model_path} (Existiert: {os.path.exists(model_path)})")

            self.p = piper.piper_api(model_path, config_path)   # Sythesizer

            lenght_scale = 200/int(self.speed)  # verändert die Geschwindigkeit

            samples = self.p.text_to_audio(text, lenght_scale)

            # Audio abspielen
            target_rate = int(pitch)*250   # verändert die Stimmlage
            wav_data = self._samples_to_wav(samples, target_rate)
            #self._play_wav(wav_data)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fp:
                self.temp_path = fp.name  # Pfad zur temporären Datei merken
                print ('Pfad zur temporären Datei  ', self.temp_path)
                with open(self.temp_path, "wb") as f:
                    f.write(wav_data)
                self._play_audio_file(fp.name)

        except Exception as e:
            print(f"Piper Fehler (Typ: {type(e)}): {e}")
            self._play_test_tone()

    def use_pyttsx4(self,text, lang_code, pitch, speed):

        if lang_code == "de":
            lang = 'German'
        elif lang_code == "it":
            lang = 'Italian'
        elif lang_code == "es":
            lang = 'Spanish'
        elif lang_code == "eo":
            lang = 'Esperanto'
        elif lang_code == "fr":
            lang = 'French'
        else:
            print ('andere Sprache funktioniert noch nicht')
            return

        engine = pyttsx4.init()
        print (lang)

        engine.setProperty('voice', lang)
        rate = int(speed)
        engine.setProperty('rate', rate)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fp:
            engine.save_to_file(text, fp.name)
            engine.runAndWait()
            self.temp_path = fp.name
            print ('Pfad zur temporären Datei  ', self.temp_path)

        self._play_audio_file(self.temp_path)

    def use_gTTS(self, text, lang_code):
        print ('lang in gTTS ', lang_code)
        try:
            #from gtts import gTTS, lang

            # Temporäre Datei erstellen
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                tts = gTTS(text=text, lang=lang_code)
                tts.save(fp.name)
                self.temp_path = fp.name  # Pfad zur temporären Datei merken
                print ('Pfad zur temporären Datei  ', self.temp_path)
                # Mit GStreamer abspielen
                self._play_audio_file(fp.name)

        except Exception as e:
            print(f"GTTS Fehler: {e}")
            self._play_test_tone()

    def save_audio_file(self, file):  # speichert Audio-File mit Auswahldialog
        shutil.move(self.temp_path, file)  # verschiebt die temporäre Datei

    def _play_audio_file(self, file_path):
        """Spielt Audio-Dateien mit GStreamer ab"""
        pipeline = Gst.parse_launch(
            f"filesrc location={file_path} ! decodebin ! audioconvert ! audioresample ! autoaudiosink"
        )
        pipeline.set_state(Gst.State.PLAYING)

        # Warte auf Ende der Wiedergabe
        bus = pipeline.get_bus()
        msg = bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.ERROR | Gst.MessageType.EOS
        )

        pipeline.set_state(Gst.State.NULL)

    def _play_raw(self, samples, rate):
        """Spielt Rohdaten mit GStreamer"""
        if not samples:
            return

        # Konfiguriere Audioformat
        caps = Gst.Caps.from_string(
            f"audio/x-raw,format=S16LE,channels=1,rate={rate},layout=interleaved"
        )
        self.src.set_property("caps", caps)

        # Starte Wiedergabe
        self.pipeline.set_state(Gst.State.PLAYING)
        buffer = Gst.Buffer.new_wrapped(samples.tobytes())
        self.src.emit("push-buffer", buffer)
        self.src.emit("end-of-stream")

        # Automatischer Stop nach der Dauer
        duration = len(samples) / rate
        GLib.timeout_add_seconds(int(duration) + 1, self._stop_pipeline)

    def _play_test_tone(self):
        """Fallback: 440Hz Sinuswelle"""
        samples = array.array('h', [
            int(32767 * math.sin(2 * math.pi * 440 * i / 22050))
            for i in range(22050)
        ])
        self._play_raw(samples, 22050)

    def _stop_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
        return False

    def _samples_to_wav(self, samples, target_rate=22050):
        audio = np.array(samples, dtype=np.int16)
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(target_rate)  # ändert Ausgabefrequenzan
                wav.writeframes(audio.tobytes())
            return wav_buffer.getvalue()


