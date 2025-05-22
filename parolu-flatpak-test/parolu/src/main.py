
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

class ParoluWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Parolu")
        self.set_default_size(600, 400)
        label = Gtk.Label(label="Parolu gestartet!")
        self.set_content(label)

class ParoluApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="im.bernard.Parolu")
    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ParoluWindow(application=self)
        win.present()

def main():
    app = ParoluApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
