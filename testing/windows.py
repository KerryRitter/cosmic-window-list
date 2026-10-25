#!/usr/bin/env python3
"""Three disposable windows from one app. Control via JSON file."""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio
import json
from pathlib import Path

control = Path(__file__).with_name("windows-control.json")
windows = {}
app = Gtk.Application(application_id="io.github.kerry.WindowListTest", flags=Gio.ApplicationFlags.NON_UNIQUE)

def activate(application):
    def create(name):
        i = len(windows)
        win = Gtk.ApplicationWindow(application=application)
        win.set_title("Window List Test — " + name)
        win.set_default_size(380, 180)
        win.move(120 + i * 50, 180 + i * 50)
        win.add(Gtk.Label(label=f"Disposable test window: {name}\nSame app, separate taskbar button."))
        win.connect("destroy", lambda _, name=name: windows.pop(name, None))
        windows[name] = win
        win.show_all()
    for name in ["Alpha", "Bravo", "Charlie"]:
        create(name)
    def poll():
        if control.exists():
            command = json.loads(control.read_text())
            control.unlink()
            if command["action"] == "quit":
                application.quit(); return False
            if command["action"] == "add":
                for name in command["names"]: create(name)
            win = windows.get(command.get("window"))
            if win:
                if command["action"] == "title": win.set_title(command["title"])
                elif command["action"] == "focus": win.present()
                elif command["action"] == "move": win.move(command['x'], command['y'])
        return True
    GLib.timeout_add(100, poll)

app.connect("activate", activate)
app.run([])
