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

        # Install EO voices
        in_path = "/app/share/eo"
        os.system(f'cp -r {in_path} {self.voices_dir}')

    def get_installed_voices(self, lang_code):
        """Gibt installierte Stimmen für eine Sprache zurück"""
        lang_dir = os.path.join(self.voices_dir, lang_code)
        voices = []

        if os.path.exists(lang_dir): # z.B. /home/walter/.var/app/im.bernard.Parolu/data/parolu/models/de
            for voice_id in os.listdir(lang_dir): # die Stimmdateien einer bestimmten Sprache
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
        # print ('Teile der Stimme  ', len(parts), parts)
        if len(parts) > 1:
            return f"{parts[1].capitalize()}" # hier wird "Kerstin" zurückgegeben
        return voice_id

    def repair_config(self, config_path):
        """Korrigiert fehlerhafte Piper-Konfigurationen vor dem Laden.

        Manche Stimmen (z.B. es_MX-ald-medium) haben "PhonemeType.ESPEAK"
        statt "espeak" als phoneme_type, was piper beim Laden ablehnt.
        """
        with open(config_path, encoding='utf-8') as f:
            config = json.load(f)

        phoneme_type = config.get('phoneme_type')
        if isinstance(phoneme_type, str) and phoneme_type.startswith('PhonemeType.'):
            config['phoneme_type'] = phoneme_type.split('.', 1)[1].lower()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

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
        """Lädt eine Stimm-Datei herunter mit Fortschrittsanzeige"""
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

    def _delete_voice(self, btn, voice_id, voice_path, dialog):
        confirm_dialog = Adw.MessageDialog(
            # ... [wie oben] ...
        )

        def handle_response(dialog, response):
            if response == "delete":
                try:
                    import shutil
                    if os.path.exists(voice_path):
                        shutil.rmtree(voice_path)
                        toast = Adw.Toast(title=f"Stimme gelöscht", timeout=2)
                        dialog.add_toast(toast)
                        self._update_voice_chooser(self.lang_code)
                        GLib.timeout_add_seconds(1, dialog.destroy)
                    else:
                        raise Exception("Stimmen-Pfad existiert nicht")
                except Exception as e:
                    btn.set_label("Fehlgeschlagen")
                    toast = Adw.Toast(title=f"Löschen fehlgeschlagen: {e}", timeout=3)
                    dialog.add_toast(toast)
                    GLib.timeout_add_seconds(3, lambda: btn.set_label("Löschen"))
                    GLib.timeout_add_seconds(3, lambda: btn.set_sensitive(True))

        confirm_dialog.connect("response", handle_response)
        confirm_dialog.present()
