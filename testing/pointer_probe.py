#!/usr/bin/env python3
"""Temporary fullscreen pointer calibration; exits when control file says hide."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from pathlib import Path
import json
root=Path(__file__).parent
display=Gdk.Display.get_default()
screen=Gdk.Screen.get_default()
windows=[]
for i in range(display.get_n_monitors()):
    monitor=display.get_monitor(i)
    rect=monitor.get_geometry()
    win=Gtk.Window(title='Window List pointer calibration')
    win.set_accept_focus(False)
    win.set_focus_on_map(False)
    win.add(Gtk.Label(label='Testing panel pointer coordinates — closes automatically'))
    win.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
    def motion(w,e,i=i,rect=rect):
        (root/'pointer.json').write_text(json.dumps({'x':rect.x+e.x,'y':rect.y+e.y,'monitor':i}))
    win.connect('motion-notify-event',motion)
    win.fullscreen_on_monitor(screen,i)
    win.show_all()
    windows.append(win)
def poll():
    p=root/'pointer-hide'
    if p.exists():
        p.unlink();Gtk.main_quit();return False
    return True
GLib.timeout_add(50,poll)
Gtk.main()
