import os
import json
from gi.repository import Gtk, Adw, GLib
import requests

class VoiceManager:
    def __init__(self, app_window):
        self.window = app_window
        self.voices_dir = os.path.join(
            GLib.get_user_data_dir(),
            "parolu",
            "models"
        )
        os.makedirs(self.voices_dir, exist_ok=True)
        print ('voices dir   ', self.voices_dir)

    def get_installed_voices(self, lang_code):
        """Gibt installierte Stimmen für eine Sprache zurück"""
        lang_dir = os.path.join(self.voices_dir, lang_code)
        voices = []
        print ('Stimmenordner der Sprache  ', lang_dir)
        if os.path.exists(lang_dir): # z.B. /home/walter/.var/app/im.bernard.Parolu/data/parolu/models/de
            for voice_id in os.listdir(lang_dir): # die Stimmdateien einer bestimmten Sprache
                print ('voice_id = ', voice_id)
                voice_path = os.path.join(lang_dir, voice_id)
                if os.path.isdir(voice_path):  # wenn voice_path ein Ordner ist
                    if self._is_valid_voice(voice_path, voice_id):
                        voices.append({
                            'id': voice_id,
                            'name': self._get_voice_name(voice_id),
                            'path': voice_path
                        })
        return voices

    def _is_valid_voice(self, voice_path, voice_id):
        """Überprüft ob Stimme vollständig ist"""
        required_files = [
            f"{voice_id}.onnx",
            f"{voice_id}.onnx.json"
        ]
        return all(os.path.exists(os.path.join(voice_path, f)) for f in required_files)

    def _get_voice_name(self, voice_id):
        """Extrahiert lesbaren Namen aus Voice-ID"""
        # Beispiel: "de_DE-kerstin-low" → "Kerstin (low)"
        parts = voice_id.split('-')
        print ('Teile der Stimme  ', len(parts), parts)
        if len(parts) > 1:
            return f"{parts[1].capitalize()} ({parts[2]})" # hier wird Kerstin (low) zurückgegeben
        return voice_id

    def download_voice(self, voice_id, model_url, config_url, progress_callback=None):
        """Lädt eine Stimme herunter und speichert sie lokal über download_file"""

        lang_code = voice_id.split('-')[0]
        voice_dir = os.path.join(self.voices_dir, lang_code, voice_id)
        os.makedirs(voice_dir, exist_ok=True)

        model_path = os.path.join(voice_dir, f"{voice_id}.onnx")
        self._download_file(model_url, model_path, progress_callback)

        config_path = os.path.join(voice_dir, f"{voice_id}.onnx.json")
        self._download_file(config_url, config_path, progress_callback)

        return voice_dir

    def _download_file(self, url, dest_path, progress_callback=None):
        """Lädt eine Datei herunter und speichert sie in dest_path"""
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
