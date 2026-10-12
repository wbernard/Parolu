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

from piper import PiperVoice, SynthesisConfig

import math
import tempfile
import io
import wave
import struct
import numpy as np
import shutil
from pathlib import Path
from .pipervoice import VoiceManager
from .vocxpo import convert_text_for_eo_voice
import threading

class Reader():
      # Konstruktor, initialisiert Eingabewerte
    def __init__(self, text, engine, lang_code, selected_voice, pitch, speed, window=None):
        self.window = window
        self.text = text
        self.engine = engine
        self.lang_code = lang_code  # de, it, eo, en
        self.pitch = pitch
        self.speed = speed
        self.selected_voice = selected_voice
        Gst.init(None)
        self._init_gstreamer()

        self._dialog_ready = threading.Event()
        self._pipeline = None
        self._current_pipeline = None

        self.voicemanager = VoiceManager(self)

        if lang_code == "eo":
            text = convert_text_for_eo_voice(text)

        self.use_piper(text, lang_code, selected_voice, pitch, speed)

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
        # print ('voice_name  = ', voice_name)
        for base_path in search_paths:
            model_path = base_path / lang_code / f"{voice_name}/{voice_name}.onnx"
            config_path = base_path / lang_code / f"{voice_name}/{voice_name}.onnx.json"
            # print ('Pfade ', model_path, config_path)
            if model_path.exists() and config_path.exists():
                return str(model_path), str(config_path)

        raise FileNotFoundError(f"Stimme {voice_name} ({lang_code}) nicht gefunden")

    def use_piper(self, text, lang_code, selected_voice, pitch, speed):
        """Hauptmethode für Sprachsynthese"""

        # 1. UI sperren und Dialog anzeigen
        GLib.idle_add(self._show_processing_ui)

        # 2. Synthese im Hintergrundthread starten
        threading.Thread(
            target=self._synthesize_audio,
            args=(text, lang_code, selected_voice, pitch, speed),
            daemon=True
        ).start()

    def _reactivate_ui(self):
        """Reaktiviert die Benutzeroberfläche"""
        if hasattr(self, 'window') and self.window:
            self.window.set_sensitive(True)
            self.window.hide_wait_dialog()

    def _show_processing_ui(self):
        """Zeigt Warte-Dialog und deaktiviert UI"""
        if self.window:
            self.window.set_sensitive(False)
            self.window.show_wait_dialog()
            self._dialog_ready.set()

    def _synthesize_audio(self, text, lang_code, voice, pitch, speed):
        """Audio-Synthese im Hintergrundthread"""
        self.temp_path = None
        try:
            # Warten bis Dialog wirklich sichtbar ist
            if not self._dialog_ready.wait(timeout=2.0):
                print("Warnung: Dialog konnte nicht angezeigt werden")

            voices = self.voicemanager.get_installed_voices(lang_code)
            for voice in voices:
                if voice['name'] == self.selected_voice:
                    voice_id = voice['id']

            model_path, config_path = self.get_voice_path(lang_code, voice_id)

            if not (os.path.exists(model_path) and os.path.exists(config_path)):
                print("❌ Modell oder Konfiguration fehlen")
                return

            self.voicemanager.repair_config(config_path)

            # We could also enable cude: with `use_cuda=True`
            self.p = PiperVoice.load(model_path, config_path)

            length_scale = 0.8/self.speed  # verändert die Geschwindigkeit

            syn_config = SynthesisConfig(
	        length_scale=length_scale
            )

            # wav Data erstellen
            self.p.config.sample_rate = pitch*19000   # verändert die Stimmlage

            # Temporäre Datei erstellen
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                with wave.open(f, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)  # 16-bit
                    self.p.synthesize_wav(text, wav, syn_config=syn_config)
                    self.temp_path = f.name

            # Dialog schließen VOR Wiedergabe
            if hasattr(self, 'window') and self.window:
                GLib.idle_add(self.window.hide_wait_dialog)
                self.window.set_sensitive(True)

            # Wiedergabe mit Reaktivierungs-Callback starten
            GLib.idle_add(
                lambda: self._play_audio_file_async(
                    self.temp_path,
                    callback=lambda: self._reactivate_ui()
                )
            )

        except Exception as e:
            GLib.idle_add(self._handle_error, str(e), self.temp_path)

    def _handle_error(self, error_msg, temp_path=None):
        """Zentrale Fehlerbehandlung"""
        print(f"Fehler: {error_msg}")
        if self.window:
            self.window.hide_wait_dialog()
            self.window.set_sensitive(True)
            self.window._show_error(error_msg)

        if self.temp_path:
            try:
                os.unlink(self.temp_path)
            except:
                pass

    def save_audio_file(self, file):  # speichert Audio-File mit Auswahldialog
        shutil.move(self.temp_path, file)  # verschiebt die temporäre Datei

    def _play_audio_file_async(self, file_path, callback=None):
        """Sichere Audio-Wiedergabe mit Fehlerbehandlung"""
        try:
            # 1. Vorherige Wiedergabe stoppen
            self.stop_audio()

            # 2. Pipeline erstellen und prüfen
            pipeline = Gst.parse_launch(
                f"filesrc location={file_path} ! decodebin ! audioconvert ! audioresample ! autoaudiosink"
            )

            if not pipeline:
                raise RuntimeError("Pipeline creation failed")

            # 3. Pipeline zuweisen NACH erfolgreicher Erstellung
            self._current_pipeline = pipeline

            # 4. Bus-Konfiguration
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message",
                   lambda bus, msg: self._on_gst_message(bus, msg, pipeline, file_path, callback))

            # 5. Wiedergabe starten
            ret = pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("Failed to set pipeline state")

        except Exception as e:
            print(f"Playback error: {e}")
            self.stop_audio()  # Bereinigen
            if callback:
                GLib.idle_add(callback)

    def _on_gst_message(self, bus, message, pipeline, file_path, callback):

        if message.type == Gst.MessageType.EOS:
            print("Playback finished")
            button = self.window.read_button
            self.window.stop_playback(button)
            if callback:
                GLib.idle_add(callback)
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Playback error: {err}, {debug}")
            if callback:
                GLib.idle_add(callback)
            pipeline.set_state(Gst.State.NULL)

    def stop_audio(self):
        """Stoppt die aktuelle Wiedergabe"""
        if self._current_pipeline:
            self._current_pipeline.set_state(Gst.State.NULL)
            self._current_pipeline = None

    def _cleanup_pipeline(self, pipeline, file_path):
        """Räumt Pipeline-Ressourcen auf"""
        if pipeline:
            pipeline.set_state(Gst.State.NULL)
            if hasattr(self, '_current_pipeline'):
                del self._current_pipeline

        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                print(f"Fehler beim Löschen: {e}")

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
        GLib.timeout_add_seconds(int(duration) + 1, self._stop_audio)

    def _play_test_tone(self):
        """Fallback: 440Hz Sinuswelle"""
        samples = array.array('h', [
            int(32767 * math.sin(2 * math.pi * 440 * i / 22050))
            for i in range(22050)
        ])
        self._play_raw(samples, 22050)
