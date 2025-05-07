# window.py
#
# Copyright 2025 walter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw
from gi.repository import Gtk, Gio, GLib

resource = Gio.Resource.load("/app/share/parolu.gresource")
Gio.Resource._register(resource)

import pyttsx4
import os
import shutil
import requests
import json
import time

from gtts import gTTS, lang

from .reader import Reader

from .pipervoice import VoiceManager

@Gtk.Template(resource_path='/im/bernard/Parolu/window.ui')
class ParoluWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ParoluWindow'

    main_text_view = Gtk.Template.Child()  # Feld für Texteingabe
    open_button = Gtk.Template.Child()     # öffnet eine Datei
    tts_chooser = Gtk.Template.Child()     # lädt tts-engine
    read_button = Gtk.Template.Child()     # spielt Audio-Datei ab
    save_button = Gtk.Template.Child()     # speichert Audio-Datei
    lang_chooser= Gtk.Template.Child()     # lädt Sprache
    pitch_chooser = Gtk.Template.Child()   # lädt Geschlecht
    speed_chooser= Gtk.Template.Child()    # lädt Sprechgeschwindigkeit
    voice_chooser= Gtk.Template.Child()    # lädt Stimme

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # die Aktion zum Öffnen einer Datei wird hinzugefügt
        open_action = Gio.SimpleAction(name="open")
        open_action.connect("activate", self.open_file_dialog)
        self.add_action(open_action)

        # die Aktion zum Speichern des Texts wird hinzugefügt
        save_text_action = Gio.SimpleAction(name="save-text-as")
        save_text_action.connect("activate", self.save_text_dialog)
        self.add_action(save_text_action)

        # die Aktion zum Speichern des Audio-files wird hinzugefügt
        save_audio_action = Gio.SimpleAction(name="save-audio-as")
        save_audio_action.connect("activate", self.save_audio_dialog)
        self.add_action(save_audio_action)

        #die Aktion zum Laden der tts-engine wird hinzugefügt
        #self.tts_chooser.connect("notify::selected-item", on_selected_engine)

        #die Aktion zum Hören des Texts wird hinzugefügt
        self.read_button.connect('clicked', self.read_text)

        #die Aktion zum  Speichern des Audio-files wird hinzugefügt
        self.save_button.connect('clicked', self.save_audio_dialog)

        ## Operationen zum Auswählen bzw Laden einer Stimme ##

        # Stimmen-API-URL
        self.voices_api = "https://raw.githubusercontent.com/rhasspy/piper/master/VOICES.md"

         # Sprachzuordnung
        self.lang_map = {
            "Deutsch": "de",
            "Italiano": "it",
            "Esperanto": "eo",
            "English": "en",
        }
        self.voicemanager = VoiceManager(self)

        # Initiale UI-Aktualisierung
        #self._update_voice_chooser()
        self._setup_lang_chooser()
        self._connect_signals()

        lang_name = self.lang_chooser.get_selected_item().get_string()
        self.lang_code = self.lang_map.get(lang_name, "en")
        print ('Sprachkodex am Beginn  ', self.lang_code)
        voices = self.voicemanager.get_installed_voices(self.lang_code)
        print ('Stimmen aus pipervoice  ', voices)

    def _connect_signals(self):
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)
        self.voice_chooser.connect("notify::selected", self._on_voice_changed)

    def _parse_voices_md(self, md_text, lang_code):
        """Parst das aktuelle Piper-Voices Markdown-Format"""
        voices = []
        current_lang = None
        current_voice = None
        # print ('Stimmen zum Download  ', md_text)
        for line in md_text.split('\n'):
            line = line.strip()

            # Sprachkategorie erkennen (z.B. "* Italian (`it_IT`, Italiano)")
            if line.startswith('* ') and '(`' in line:
                lang_parts = line.split('`')
                # print ('Teile der Stimme  ', lang_parts)
                if len(lang_parts) > 1:
                    current_lang = lang_parts[1].split('_')[0]  # Extrahiert "it" aus "it_IT"
                    current_voice = None

            # Nur Stimmen der gewählten Sprache verarbeiten
            if current_lang != lang_code:  # wenn andere Sprache wird Rest übersprungen
                continue

            # Stimmenname erkennen (z.B. "* paola")
            if line.startswith('* ') and not '(`' in line and not 'http' in line:
                current_voice = line.split('*')[1].strip()
                print ('aktuelle Stimme  ', current_voice)

            # Qualität und URLs erkennen (z.B. "* medium - [[model](http...)]")
            if current_voice and line.startswith('* ') and 'http' in line:
                quality = line.split('*')[1].split('-')[0].strip()
                urls = [u.split('(')[1].split(')')[0] for u in line.split('[') if 'http' in u]
                print ('urls der Stimme', urls)
                if urls and len(urls) >= 2:
                    voices.append({
                        'id': f"{lang_code}_{current_voice}_{quality}",
                        'name': f"{current_voice} ({quality})",
                        'model_url': urls[0],  # Erste URL ist das Modell
                        'config_url': urls[1],  # Zweite URL ist die Konfig
                        'quality': quality
                    })

        return voices or [{'id': f"{lang_code}_default", 'name': "Standard-Stimme"}]

    def _setup_lang_chooser(self):
        # Signal vorübergehend deaktivieren
        # self.lang_chooser.disconnect_by_func(self._on_lang_changed)

        # Aktuelle Sprache auswählen
        lang_name = self.lang_chooser.get_selected_item().get_string()
        self.lang_code = self.lang_map.get(lang_name, "en")
        self._update_voice_chooser(self.lang_code)
        print ('gewählte Sprache   ', lang_name)
        # Signal wieder verbinden
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)

    def _on_lang_changed(self, dropdown, _):
        lang_name = self.lang_chooser.get_selected_item().get_string()
        print ('neue Sprache angeklickt', lang_name)
        self.lang_code = self.lang_map.get(lang_name, "en")
        self._update_voice_chooser(self.lang_code)

    def _on_voice_changed(self, dropdown, _):
        selected = dropdown.get_selected()
        model = dropdown.get_model()

        if selected == model.get_n_items() - 1:  # "Andere Stimme..." ausgewählt
            self._show_voice_download_dialog()

    def _update_voice_chooser(self, lang_code):
        """Aktualisiert die Dropdown-Auswahl"""
        voices = self.voicemanager.get_installed_voices(lang_code)
        print ('lang_code in voice_chooser  ', lang_code)
        print ('verfügbare voices  ', voices)

        model = Gtk.StringList.new()
        for voice in voices:
            model.append(voice['name'])
        model.append("Andere Stimme herunterladen...")

        self.voice_chooser.set_model(model)
        self.voice_chooser.set_selected(0)   # stellt Auswahlfenster auf die erste Zeile

    # @Gtk.Template.Callback()
    # def on_voice_chooser_changed(self, dropdown):   # bei Änderung in voice_chooser
    #     selected = dropdown.get_selected()          # wird voic_download_
    #     model = dropdown.get_model()

    #     if selected == model.get_n_items() - 1:  # Letzter Eintrag ("Andere Stimme...")
    #         self._show_voice_download_dialog()

    # @Gtk.Template.Callback()
    def on_voice_download_selected(self, *args):
        """Handhabt die Auswahl von 'Andere Stimme'"""
        self._show_voice_download_dialog()

    # def _show_voice_download_dialog(self):
    #     """Zeigt Dialog mit Stimmenauswahl"""
    #     dialog = Adw.MessageDialog(
    #         transient_for=self,
    #         heading="Stimmen herunterladen",
    #         body="Bitte warten..."
    #     )

        # Erstelle ListBox für Stimmen
    #     self.voice_list = Gtk.ListBox()
    #     scrolled = Gtk.ScrolledWindow()
    #     scrolled.set_child(self.voice_list)
    #     dialog.set_extra_child(scrolled)

        # Lade Stimmen im Hintergrund
    #     GLib.idle_add(self._populate_voice_list, dialog)
    #     dialog.present()

    # def _populate_voice_list(self, dialog):
    #     try:
    #         lang_index = self.lang_chooser.get_selected()
    #         lang_code = self.lang_map.get(self.lang_chooser.get_model().get_item(lang_index).get_string(), "en")

    #         response = requests.get(self.voices_api)
    #         print ('## jetzt rufe ich parce_voices mit lang_index und lang_code ',lang_index, lang_code)
    #         voices = self._parse_voices_md(response.text, lang_code)
    #         print ('Verfügbare Stimmen in populate Voices', voices)
    #         for voice in voices:
    #             row = Adw.ActionRow(title=voice['name'])
    #             btn = Gtk.Button(label="Installieren")
    #             btn.connect('clicked', lambda *_, v=voice: self._install_voice(v['id']))
    #             row.add_suffix(btn)
    #             self.voice_list.append(row)

    #         dialog.set_body(f"{len(voices)} Stimmen verfügbar")
    #     except Exception as e:
    #         dialog.set_body(f"Fehler: {str(e)}")

    def _show_voice_download_dialog(self):
        """Zeigt Download-Dialog an"""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Neue Stimme herunterladen"
        )

        # Lade verfügbare Stimmen vom Server
        available_voices = self._fetch_available_voices()
        print ('======= Verfügbare Stimmen  ', available_voices)
        # Erstelle Auswahl-Liste
        listbox = Gtk.ListBox()
        for voice in available_voices:
            row = Adw.ActionRow(title=voice['name'])
            btn = Gtk.Button(label="Installieren")
            btn.connect('clicked', self._on_voice_selected, voice['id'], voice['model_url'], voice['config_url'], dialog)
            row.add_suffix(btn)
            listbox.append(row)

        dialog.set_extra_child(listbox)
        dialog.present()

    def _fetch_available_voices(self):
        """Lädt verfügbare Stimmen von der Piper GitHub-Seite oder lokal zwischengespeichert"""
        try:
            # 1. Versuche, von GitHub zu laden
            response = requests.get(
                "https://raw.githubusercontent.com/rhasspy/piper/master/VOICES.md",
                timeout=10  # Timeout nach 10 Sekunden
            )
            response.raise_for_status()  # Wirft Exception bei HTTP-Fehlern

            # 2. Parse die Markdown-Antwort
            print ('### jetzt rufe ich aus fetch_available parse_voices auf', self.lang_code)
            voices = self._parse_voices_md(response.text, self.lang_code)

            # 3. Cache die Stimmen lokal
            cache_dir = os.path.join(GLib.get_user_cache_dir(), "parolu")
            os.makedirs(cache_dir, exist_ok=True)

            cache_file = os.path.join(cache_dir, "voices_cache.json")
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'voices': voices,
                    'lang': self.lang_code
                }, f)

            return voices

        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Netzwerkfehler: {e}. Versuche Cache...")
            return self._load_cached_voices(lang_code)

    def _load_cached_voices(self, lang_code):
        """Lädt zwischengespeicherte Stimmen falls Online-Laden fehlschlägt"""
        cache_file = os.path.join(
            GLib.get_user_cache_dir(),
            "parolu",
            "voices_cache.json"
        )

        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Nur zurückgeben wenn gleiche Sprache oder keine Sprache gefiltert
                    if not lang_code or data.get('lang') == lang_code:
                        return data['voices']
            except Exception as e:
                print(f"Cache-Fehler: {e}")

        # Fallback-Stimme
        return [{
            'id': f"{lang_code}_default" if lang_code else "default",
            'name': "Standard-Stimme",
            'quality': "medium"
        }]

    def _on_voice_selected(self, btn, voice_id, model_url, config_url, dialog):
        """Installiert die ausgewählte Stimme"""
        dialog.set_body("Download läuft...")
        lang_code = self.lang_code
        print ('voice_id in on_voice selected =  ', voice_id, 'Sprache', lang_code)
        def on_progress(progress):
            dialog.set_body(f"Download: {progress}%")

        def on_complete():
            dialog.destroy()

            self._update_voice_chooser(lang_code)

        self.voicemanager.download_voice(
            voice_id, model_url, config_url,
            progress_callback=on_progress
        )
        GLib.idle_add(on_complete)

    ## ================================================================##
    # Dialog zum Öffnen einer Datei wird definiert
    def open_file_dialog(self, action, _):
        # Create a new file selection dialog, using the "open" mode
        native = Gtk.FileDialog()
        native.open(self, None, self.on_open_response)

    # Dialog zum Speichern einer Text-Datei wird definiert
    def save_text_dialog(self, action, _):
        native = Gtk.FileDialog()
        native.save(self, None, self.on_save_text_response)

    # Dialog zum Speichern einer Audio-Datei wird definiert
    def save_audio_dialog(self, action):
        native = Gtk.FileDialog()
        native.save(self, None, self.on_save_audio_response)

    # definiert was geschieht wenn Datei ausgewählt/nicht ausgewählt wurde
    def on_open_response(self, dialog, result):
        file = dialog.open_finish(result)
        # If the user selected a file...
        if file is not None:
            # ... open itgit
            self.open_file(file)

    # definiert was geschieht wenn Text-Datei ausgewählt/nicht ausgewählt wurde
    def on_save_text_response(self, dialog, result):
        file = dialog.save_finish(result)
        if file is not None:
            self.save_text(file)

    # definiert was geschieht wenn Audio-Datei ausgewählt/nicht ausgewählt wurde
    def on_save_audio_response(self, dialog, result):
        file = dialog.save_finish(result)
        if file is not None:
            #self.read.safe_audio_file()
            self.read.save_audio_file(file)

    # Inhalt der Textdatei wird asynchron geöffnet um die Anwendung nicht zu blockieren
    def open_file(self, file):
        file.load_contents_async(None, self.open_file_complete)

    # wird aufgerufen wenn das Einlesen fertig oder ein Fehler aufgetreten ist
    def open_file_complete(self, file, result):

        contents = file.load_contents_finish(result)  # enthält boolsche Variable, den eingelesenen Text, u.a.

        if not contents[0]:
            path = file.peek_path()
            print(f"Unable to open {path}: {contents[1]}")
            return

        # Kontrolle ob der eingelesene Inhalt ein Text ist
        try:
            text = contents[1].decode('utf-8')
        except UnicodeError as err:
            path = file.peek_path()
            print(f"Unable to load the contents of {path}: the file is not encoded with UTF-8")
            return

        buffer = self.main_text_view.get_buffer()
        buffer.set_text(text)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)

    def save_text(self, file):
        buffer = self.main_text_view.get_buffer()

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        # If there is nothing to save, return early
        if not text:
            return

        bytes = GLib.Bytes.new(text.encode('utf-8'))

        # Start the asynchronous operation to save the data into the file
        file.replace_contents_bytes_async(bytes,
                                          None,
                                          False,
                                          Gio.FileCreateFlags.NONE,
                                          None,
                                          self.save_text_complete)

    def save_text_complete(self, file, result):
        res = file.replace_contents_finish(result)
        info = file.query_info("standard::display-name",
                               Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()
        if not res:
            print(f"Unable to save {display_name}")

    # Abspielen des Texts
    def read_text(self, button):

        print ('### Audio abspielen   ###')
        buffer = self.main_text_view.get_buffer()

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        engine = self.tts_chooser.get_selected_item().get_string()
        print(engine)

        lang_name = self.lang_chooser.get_selected_item().get_string()
        print(lang_name)

        pitch = self.pitch_chooser.get_selected_item().get_string()
        print(pitch)

        speed = self.speed_chooser.get_selected_item().get_string()
        print(speed)

        self.read = Reader(text, engine, self.lang_code, pitch, speed)


