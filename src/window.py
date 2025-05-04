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
        self.voice_mgr = VoiceManager(self)

        # Initiale UI-Aktualisierung
        #self._update_voice_chooser()
        self._setup_lang_chooser()
        self._connect_signals()

        lang_name = self.lang_chooser.get_selected_item().get_string()
        self.lang_code = self.lang_map.get(lang_name, "en")
        print ('Sprachkodex am Beginn  ', self.lang_code)
        voices = self.voice_mgr.get_installed_voices(self.lang_code)
        print ('Stimmen aus pipervoice  ', voices)

    def _connect_signals(self):
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)
        self.voice_chooser.connect("notify::selected", self._on_voice_changed)

    def _parse_voices_md(self, md_text, lang_code):
        """Parst das neue Markdown-Format von Piper Voices"""
        voices = []
        current_lang = None
        # print ('Stimmen zum Download  ', md_text)
        for line in md_text.split('\n'):
            # Sprachkategorie erkennen (z.B. "German (`de_DE`, Deutsch)")
            if line.startswith('* ') and '(`' in line:
                parts = line.split('`')
                if len(parts) > 1:  # liest für jede angebotene Stimme den lang_code aus
                    current_lang = parts[1].split('_')[0]  # Extrahiert "de" aus "de_DE"
                    print ('Sprachcodex  ', current_lang)
            # Stimmen erkennen (nur wenn in der richtigen Sprache)
            if current_lang == lang_code and line.strip().startswith('* *'):
                voice_parts = line.split('*')
                print ('voice_parts  ', voice_parts)
                if len(voice_parts) >= 3:
                    voice_name = voice_parts[2].strip()
                    quality = voice_parts[3].split('-')[0].strip() if len(voice_parts) > 3 else "medium"

                    # Extrahiere Voice-ID (z.B. "de_DE-eva_k-x_low")
                    url_start = line.find('https://huggingface.co/')
                    print ('url startet  ', url_start)
                    if url_start > 0:
                        url = line[url_start:].split('?')[0]
                        voice_id = url.split('/')[-3] + '-' + voice_name + '-' + quality.lower()
                        voices.append({
                            'id': voice_id,
                            'name': f"{voice_name} ({quality})",
                            'quality': quality
                        })

        return voices or [{'id': f"{lang_code}_default", 'name': "Standard-Stimme"}]

    def _setup_lang_chooser(self):
        # Signal vorübergehend deaktivieren
        # self.lang_chooser.disconnect_by_func(self._on_lang_changed)

        # Aktuelle Sprache auswählen
        current_lang = self.lang_chooser.get_selected()
        self._update_voice_chooser(current_lang)
        print ('current_lang   ', current_lang)
        # Signal wieder verbinden
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)

    def _on_lang_changed(self, dropdown, _):
        lang_index = dropdown.get_selected()
        print ('neue Sprache angeklickt', lang_index)
        self._update_voice_chooser(lang_index)

    def _on_voice_changed(self, dropdown, _):
        selected = dropdown.get_selected()
        model = dropdown.get_model()

        if selected == model.get_n_items() - 1:  # "Andere Stimme..." ausgewählt
            self._show_voice_download_dialog()

    def _update_voice_chooser(self, lang_index):
        """Aktualisiert die Dropdown-Auswahl"""
        lang_name = self.lang_chooser.get_selected_item().get_string()
        lang_code = self.lang_map.get(lang_name, "en")
        voices = self.voice_mgr.get_installed_voices(lang_code)
        print ('lang_name lang_code ', lang_name, lang_code)
        print ('verfügbare voices  ', voices)

        model = Gtk.StringList.new()
        for voice in voices:
            model.append(voice['name'])
        model.append("Andere Stimme herunterladen...")

        self.voice_chooser.set_model(model)
        self.voice_chooser.set_selected(0)

    # @Gtk.Template.Callback()
    def on_voice_chooser_changed(self, dropdown):
        selected = dropdown.get_selected()
        model = dropdown.get_model()

        if selected == model.get_n_items() - 1:  # Letzter Eintrag ("Andere Stimme...")
            self._show_voice_download_dialog()

    # @Gtk.Template.Callback()
    def on_voice_download_selected(self, *args):
        """Handhabt die Auswahl von 'Andere Stimme'"""
        self._show_voice_download_dialog()

    def _show_voice_download_dialog(self):
        """Zeigt Dialog mit Stimmenauswahl"""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Stimmen herunterladen",
            body="Bitte warten..."
        )

        # Erstelle ListBox für Stimmen
        self.voice_list = Gtk.ListBox()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.voice_list)
        dialog.set_extra_child(scrolled)

        # Lade Stimmen im Hintergrund
        GLib.idle_add(self._populate_voice_list, dialog)
        dialog.present()

    def _populate_voice_list(self, dialog):
        try:
            lang_index = self.lang_chooser.get_selected()
            lang_code = self.lang_map.get(self.lang_chooser.get_model().get_item(lang_index).get_string(), "en")

            response = requests.get(self.voices_api)
            voices = self._parse_voices_md(response.text, lang_code)
            print ('Verfügbare Stimmen in populate Voices', voices)
            for voice in voices:
                row = Adw.ActionRow(title=voice['name'])
                btn = Gtk.Button(label="Installieren")
                btn.connect('clicked', lambda *_, v=voice: self._install_voice(v['id']))
                row.add_suffix(btn)
                self.voice_list.append(row)

            dialog.set_body(f"{len(voices)} Stimmen verfügbar")
        except Exception as e:
            dialog.set_body(f"Fehler: {str(e)}")

    # def _show_voice_download_dialog(self):
    #     """Zeigt Download-Dialog an"""
    #     dialog = Adw.MessageDialog(
    #         transient_for=self,
    #         heading="Neue Stimme herunterladen"
    #     )

        # Lade verfügbare Stimmen vom Server
    #     available_voices = self._fetch_available_voices()

        # Erstelle Auswahl-Liste
    #     listbox = Gtk.ListBox()
    #     for voice in available_voices:
    #         row = Adw.ActionRow(title=voice['name'])
    #         btn = Gtk.Button(label="Installieren")
    #         btn.connect('clicked', self._on_voice_selected, voice['id'], dialog)
    #         row.add_suffix(btn)
    #         listbox.append(row)

    #     dialog.set_extra_child(listbox)
    #     dialog.present()

    def _on_voice_selected(self, btn, voice_id, dialog):
        """Installiert die ausgewählte Stimme"""
        dialog.set_body("Download läuft...")

        def on_progress(progress):
            dialog.set_body(f"Download: {progress}%")

        def on_complete():
            dialog.destroy()
            self._update_voice_chooser()

        self.voice_mgr.download_voice(
            voice_id,
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


