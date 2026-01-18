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
from gi.repository import Gtk, Gio, GLib, Gdk


import os
import shutil
import requests
import json
import time
import threading

from .reader import Reader

from .pipervoice import VoiceManager

import gettext   # braucht es, damit Unterstrich übersetzbar bedeutet
_ = gettext.gettext

display = Gdk.Display.get_default()
if display:
    icon_theme = Gtk.IconTheme.get_for_display(display)
    icon_theme.add_search_path("/app/share/icons")

@Gtk.Template(resource_path='/im/bernard/Parolu/window.ui')
class ParoluWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ParoluWindow'

    main_text_view = Gtk.Template.Child()  # Feld für Texteingabe
    open_button = Gtk.Template.Child()     # öffnet eine Datei
    save_text_button = Gtk.Template.Child()     # speichert den Text
    read_button = Gtk.Template.Child()     # spielt Audio-Datei ab
    save_button = Gtk.Template.Child()     # speichert Audio-Datei
    lang_chooser= Gtk.Template.Child()     # lädt Sprache
    pitch_chooser = Gtk.Template.Child()   # lädt Geschlecht
    speed_chooser= Gtk.Template.Child()    # lädt Sprechgeschwindigkeit
    voice_chooser= Gtk.Template.Child()    # lädt Stimme
    label_1 = Gtk.Template.Child()         # zeigt Stimmlage an
    adjustment_1 = Gtk.Template.Child()    # Wert der Stimmlage
    label_2 = Gtk.Template.Child()         # zeigt Geschwindigkeit an
    adjustment_2 = Gtk.Template.Child()    # Wert der Geschwindigkeit


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.is_playing = False

        # die Aktion zum Öffnen einer Datei wird hinzugefügt
        open_action = Gio.SimpleAction(name="open")
        open_action.connect("activate", self.open_file_dialog)
        self.add_action(open_action)

        # die Aktion zum Speichern des Texts wird hinzugefügt
        save_action = Gio.SimpleAction(name="save-as")
        save_action.connect("activate", self.save_text_dialog)
        self.add_action(save_action)

        # die Aktion zum Speichern des Audio-files wird hinzugefügt
        save_audio_action = Gio.SimpleAction(name="save-audio-as")
        save_audio_action.connect("activate", self.save_audio_dialog)
        self.add_action(save_audio_action)

        #die Aktion zum Hören des Texts wird hinzugefügt
        self.read_button.connect('clicked', self.read_text)

        #die Aktion zum  Speichern des Audio-files wird hinzugefügt
        self.save_button.connect('clicked', self.save_audio_dialog)

        #die Aktion beim Ändern der Stimmlage wird hinzugefügt
        self.adjustment_1.connect("value-changed", self.on_adjustment_value_changed)

        #die Aktion beim Ändern der Geschwindigkeit wird hinzugefügt
        self.adjustment_2.connect("value-changed", self.on_adjustment_value_changed)

        ## Operationen zum Auswählen bzw Laden einer Stimme ##
        # ======================================================================
        # Stimmen-API-URL hier können die piper-Stimmen heruntergeladen werden
        self.voices_api = "https://raw.githubusercontent.com/rhasspy/piper/master/VOICES.md"

         # Sprachzuordnung
        self.lang_map = {
            "Esperanto": "eo",
            "Deutsch": "de",
            "Italiano": "it",
            "Español": "es",
            "Francais": "fr",
        }
        self.voicemanager = VoiceManager(self)

        # Initiale UI-Aktualisierung
        self._connect_signals()
        self._setup_lang_chooser()

        lang_name = self.lang_chooser.get_selected_item().get_string()
        self.lang_code = self.lang_map.get(lang_name)

        # HACK: This should be in the UI file, but for some reason style classes are not applied
        GLib.idle_add(self.get_style_context().add_class, "view")

    def show_wait_dialog(self):
        self.wait_dialog = Gtk.Dialog(
           title= _("Synchronizing"),
            transient_for=self,
            modal=True
        )
        # Größe des Dialogs festlegen
        self.wait_dialog.set_default_size(200, 80)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        # Randabstände hinzufügen
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Label mit Ausrichtung
        label = Gtk.Label(label=_("Please wait..."))
        label.set_halign(Gtk.Align.CENTER)
        box.append(label)

        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        box.append(self.spinner)

        self.wait_dialog.set_child(box)
        self.wait_dialog.show()

    def hide_wait_dialog(self):
        if hasattr(self, 'wait_dialog') and self.wait_dialog:
            self.wait_dialog.destroy()
        if hasattr(self, 'spinner') and self.spinner:
            self.spinner.stop()

    def _show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.connect("response", lambda d, _: d.destroy())
        dialog.show()

    def _connect_signals(self):
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)
        self.voice_chooser.connect("notify::selected", self._on_voice_changed)

    def _setup_lang_chooser(self):
        # Signal vorübergehend deaktivieren
        self.lang_chooser.disconnect_by_func(self._on_lang_changed)

        # Aktuelle Sprache auswählen
        lang_name = self.lang_chooser.get_selected_item().get_string()
        self.lang_code = self.lang_map.get(lang_name)
        self._update_voice_chooser(self.lang_code)
        # print ('gewählte Sprache   ', lang_name)
        # Signal wieder verbinden
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)

    def _on_lang_changed(self, dropdown, _):
        lang_name = self.lang_chooser.get_selected_item().get_string()
        self.lang_code = self.lang_map.get(lang_name)
        self._update_voice_chooser(self.lang_code)

    def _on_voice_changed(self, dropdown, _):
        selected = dropdown.get_selected()
        n_items = dropdown.get_model().get_n_items()
        if selected == n_items - 1:  # letzte Zeile ausgewählt
            if self.lang_code != "eo":
                self._show_voice_manage_dialog()

    def _update_voice_chooser(self, lang_code):
        """Aktualisiert die Dropdown-Auswahl"""
        voices = self.voicemanager.get_installed_voices(lang_code)
        # print ('lang_code in voice_chooser  ', lang_code)
        # print ('verfügbare voices  ', voices)

        model = Gtk.StringList.new()
        for voice in voices:
            model.append(voice['name'])
            # print ('Namen der Stimme voice[name]  = ', voice['name'])

        if lang_code != "eo":  # für Esperanto gibt es aktuell keine Stimmen
            model.append(_("Manage Voices…"))

        self.voice_chooser.set_model(model)
        self.voice_chooser.set_selected(0)   # stellt Auswahlfenster auf die erste Zeile

    def _show_voice_manage_dialog(self):
        dialog = Adw.Window(
            transient_for=self,
            modal=True,
            title="",  # Leerer Titel verhindert doppelte Anzeige
            default_width=500,
            default_height=300,
            deletable=True  # X-Button aktivieren
        )

        # Hauptcontainer mit HeaderBar
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Custom HeaderBar ohne doppelte Titelleiste
        header_bar = Adw.HeaderBar()
        title = Adw.WindowTitle(title=_("Manage Voices"))
        header_bar.set_title_widget(title)
        main_box.append(header_bar)

        # Scrollbereich für die Liste
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)

        # Stimmen laden und filtern
        available_voices = self._fetch_available_voices()
        installed_voices = self.voicemanager.get_installed_voices(self.lang_code)
        installed_ids = {v['id'] for v in installed_voices}
        # Fortschrittsanzeigen Dictionary
        self.download_progress = {}

        for voice in available_voices:

            row = Adw.ActionRow(title=voice['name'],
                                  margin_start=12,
                                  margin_end=12)

            if voice['id'] in installed_ids:

                # Get the path
                path = next(item['path'] for item in installed_voices if item['id'] == voice['id'])

                # Löschen-Button
                btn = Gtk.Button(label=_("Delete"),
                               css_classes=["suggested-action"])
                btn.connect('clicked', self._delete_voice,
                          voice['id'], path , dialog)

            else:
                # Fortschrittsbalken
                progress = Gtk.ProgressBar(
                    show_text=True,
                    visible=False,
                    margin_end=12
                )
                self.download_progress[voice['id']] = progress

                # Installations-Button
                btn = Gtk.Button(label="Install",
                               css_classes=["suggested-action"])
                btn.connect('clicked', self._on_voice_selected,
                          voice['id'], voice['model_url'], voice['config_url'], dialog)
                row.add_suffix(progress)

            row.add_suffix(btn)
            listbox.append(row)

        scrolled.set_child(listbox)
        main_box.append(scrolled)
        dialog.set_content(main_box)
        dialog.present()

    def _fetch_available_voices(self):
        # Lädt verfügbare Stimmen von der Piper GitHub-Seite oder lokal zwischengespeichert
        try:
            #1. Versuche, von GitHub zu laden
            response = requests.get(
                self.voices_api,
                timeout=20  # Timeout nach 10 Sekunden
            )
            # print (' ===========0===== , reponse', response.text) # response liest alle verfügbaren Stimmen ein
            response.raise_for_status()  # Wirft Exception bei HTTP-Fehlern

            #2. Parse die Markdown-Antwort
            # print ('### jetzt rufe ich aus fetch_available parse_voices auf für  ', self.lang_code)
            voices = self._parse_voices_md(response.text, self.lang_code)

            #3. Cache die Stimmen lokal
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
                # print ('aktuelle Stimme  ', current_voice)

            # Qualität und URLs erkennen (z.B. "* medium - [[model](http...)]")
            if current_voice and line.startswith('* ') and 'http' in line:
                quality = line.split('*')[1].split('-')[0].strip()
                urls = []
                parts = line.split('[')  # Teile die Zeile an den '['
                for part in parts:
                    if 'http' in part:
                        # Extrahiere den Teil zwischen '(' und ')'
                        start = part.find('(')
                        end = part.find(')')
                        if start != -1 and end != -1 and start < end:
                            url = part[start + 1:end]
                            urls.append(url)
                if urls[1].endswith(".json"): # wenn in der confi-Datei nach True .json steht
                    urls[1] = urls[1][:-5]

                # print ('---------- urls der Stimme in parse', urls)
                if urls and len(urls) >= 2:
                    voices.append({
                        'id': f"{lang_code}-{current_voice}-{quality}",
                        'name': f"{current_voice} ({quality})",
                        'model_url': urls[0],  # Erste URL ist das Modell
                        'config_url': urls[1],  # Zweite URL ist die Konfig
                        'quality': quality
                    })
        # print ('##### voices aus parse', voices)

        return voices or [{'id': f"{lang_code}_default", 'name': "Default Voice"}]

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
            'name': "Default Voice",
            'quality': "medium"
        }]

    def _on_voice_selected(self, btn, voice_id, model_url, config_url, dialog):
        """Installiert die ausgewählte Stimme mit Fortschrittsanzeige"""
        lang_code = self.lang_code
        # print(f'Installiere Stimme: {voice_id}, Sprache: {lang_code}')

        # UI-Elemente vorbereiten
        btn.set_sensitive(False)
        btn.set_label(_("Installing..."))

        # Fortschrittsanzeige holen (aus self.download_progress)
        progress = self.download_progress.get(voice_id)
        if progress:
            GLib.idle_add(progress.set_visible, True)
            GLib.idle_add(progress.set_fraction, 0.0)
            GLib.idle_add(progress.set_text, "Vorbereitung... 0%")

        # Callbacks für Fortschritt
        def on_progress(downloaded, total_size):
            fraction = downloaded / total_size if total_size > 0 else 0
            percent = int(fraction * 100)

            if progress:
                GLib.idle_add(progress.set_fraction, fraction)
                GLib.idle_add(progress.set_text, f"Download: {percent}%")
            else:
                GLib.idle_add(dialog.set_title, f"Download: {percent}%")

        def on_complete():
            if progress:
                GLib.idle_add(progress.set_text, _("Installation completed"))
                GLib.idle_add(progress.set_fraction, 1.0)

            GLib.idle_add(btn.set_label, _("Installed"))
            GLib.idle_add(btn.get_style_context().remove_class, "suggested-action")
            GLib.idle_add(self._update_voice_chooser, lang_code)

            # Dialog nach 3 Sekunden schließen
            GLib.timeout_add_seconds(3, dialog.destroy)

        def on_error(error):
            print(f"Download fehlgeschlagen: {error}")
            GLib.idle_add(btn.set_label, "Erneut versuchen")
            GLib.idle_add(btn.set_sensitive, True)
            if progress:
                GLib.idle_add(progress.set_text, f"Fehler: {str(error)}")
                GLib.idle_add(progress.get_style_context().add_class, "error")

        # Download-Thread
        def download_thread():
            try:
                self.voicemanager.download_voice(
                    voice_id,
                    model_url,
                    config_url,
                    progress_callback=on_progress
                )
                on_complete()
            except Exception as e:
                on_error(e)

        threading.Thread(target=download_thread, daemon=True).start()

    def _delete_voice(self, btn, voice_id, voice_path, parent_window):
        """Löscht eine Stimme mit korrekter Fehlerbehandlung"""

        # Bestätigungsdialog
        confirm_dialog = Adw.MessageDialog(
            transient_for=parent_window,
            heading="Delete Voice?",
            body=f"Should the voice '{voice_id}' be deleted irreversibly?",
        )

        confirm_dialog.add_response("cancel", "Cancel")
        confirm_dialog.add_response("delete", "Delete")
        confirm_dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        # Temporär Button deaktivieren
        btn.set_sensitive(False)
        btn.set_label("Deleting…")

        def on_response(dialog, response):
            if response == "delete":
                try:
                    import shutil
                    if os.path.exists(voice_path):
                        shutil.rmtree(voice_path)

                        # Erfolgsmeldung in neuem Dialog
                        success_dialog = Adw.MessageDialog(
                            transient_for=parent_window,
                            heading="Voice deleted",
                            body=f"The voice '{voice_id}' was deleted successfully"
                        )
                        success_dialog.add_response("ok", "OK")
                        success_dialog.connect("response", lambda *_: (
                            parent_window.destroy(),
                            self._update_voice_chooser(self.lang_code)
                        ))
                        success_dialog.present()

                    else:
                        raise Exception("Voice path does not exist")

                except Exception as e:
                    print(f"Löschfehler: {e}")
                    btn.set_label("Try again")
                    btn.set_sensitive(True)

                    # Fehlermeldung in neuem Dialog
                    error_dialog = Adw.MessageDialog(
                        transient_for=parent_window,
                        heading="Deletion failed",
                        body=f"Fehler: {str(e)}"
                    )
                    error_dialog.add_response("ok", "OK")
                    error_dialog.present()
            else:
                # Bei Abbruch Button zurücksetzen
                btn.set_label("Delete")
                btn.set_sensitive(True)

        confirm_dialog.connect("response", on_response)
        confirm_dialog.present()

    ## ================================================================##
    # Dialog zum Öffnen einer Datei wird definiert
    def open_file_dialog(self, action, _):
        # Create a new file selection dialog, using the "open" mode
        native = Gtk.FileDialog()
        native.open(self, None, self.on_open_response)

    # Dialog zum Speichern einer Text-Datei wird definiert
    def save_text_dialog(self, action, _):
        native = Gtk.FileDialog()
        native.set_initial_name("text.txt")
        native.save(self, None, self.on_save_text_response)

    # Dialog zum Speichern einer Audio-Datei wird definiert
    def save_audio_dialog(self, action):
        native = Gtk.FileDialog()
        native.set_initial_name("audio.wav")
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
            self.reader.save_audio_file(file)

    # definiert was geschieht wenn Stimmlage geändert wird
    def on_adjustment_value_changed(self, adjustment):
        value = adjustment.get_value()
        if adjustment == self.adjustment_1:
            self.label_1.set_text(f"× {value:.1f}")
        else:
            self.label_2.set_text(f"× {value:.1f}")

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
        # print ('### Audio abspielen   ###')
        buffer = self.main_text_view.get_buffer()

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        engine = 'piper'
        # print(engine)

        pitch = self.pitch_chooser.get_value()
        # print('pitch', pitch)

        speed = self.speed_chooser.get_value()
        # print('speed', speed)

        selected_voice = self.voice_chooser.get_selected_item().get_string()
        # print('Stimme', selected_voice)

        #self.reader = Reader(text, engine, self.lang_code, selected_voice, pitch, speed, window=self)
        # print ('is_playing:', self.is_playing)
        if self.is_playing:
            self.stop_playback(button)
        else:
            self.start_playback(button, text, engine, self.lang_code, selected_voice, pitch, speed)


    def start_playback(self, button, text, engine, lang_code, selected_voice, pitch, speed):
        """Startet die Wiedergabe und aktualisier t UI"""
        if not self.is_playing:
            #self.read_text(button)  # Deine bestehende Methode
            self.reader = Reader(text, engine, self.lang_code, selected_voice, pitch, speed, window=self)

            self.is_playing = True
            button.set_icon_name("media-playback-stop-symbolic")

    def stop_playback(self, button):
        """Stoppt die Wiedergabe und aktualisiert UI"""
        if self.is_playing:
            # Hier müsstest du den Reader stoppen - je nach Implementierung:
            if hasattr(self, 'reader') and self.reader:
                self.reader.stop_audio()  # Annahme: dein Reader hat eine stop()-Methode
            self.is_playing = False
            button.set_icon_name("media-playback-start-symbolic")

