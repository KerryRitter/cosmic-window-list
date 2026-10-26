#!/usr/bin/env python3
"""Window List settings and the supported COSMIC panel applet configuration."""
import datetime
import json
from pathlib import Path
import re
import shutil
import sys
import appearance

APP_ID = 'io.github.kerry.CosmicWindowList'
CONFIG = Path.home() / '.config/cosmic' / APP_ID / 'v1'
PANEL = Path.home() / '.config/cosmic/com.system76.CosmicPanel.Panel/v1'
SYSTEM_PANEL = Path('/usr/share/cosmic/com.system76.CosmicPanel.Panel/v1')
ICONS = [
    ('Keyboard / input source', 'com.system76.CosmicAppletInputSources', 'right'),
    ('Accessibility', 'com.system76.CosmicAppletA11y', 'right'),
    ('Window tiling controls', 'com.system76.CosmicAppletTiling', 'right'),
    ('Bluetooth', 'com.system76.CosmicAppletBluetooth', 'right'),
    ('Notifications', 'com.system76.CosmicAppletNotifications', 'right'),
    ('Workspaces', 'com.system76.CosmicPanelWorkspacesButton', 'left'),
    ('Applications', 'com.system76.CosmicPanelAppButton', 'left'),
]
ORDER = {
    'left': ['com.system76.CosmicPanelLauncherButton', 'com.system76.CosmicPanelWorkspacesButton',
             'com.system76.CosmicPanelAppButton', APP_ID, 'com.system76.CosmicAppletMinimize'],
    'right': ['com.system76.CosmicAppletInputSources', 'com.system76.CosmicAppletStatusArea',
              'com.system76.CosmicAppletA11y', 'com.system76.CosmicAppletTiling',
              'com.system76.CosmicAppletAudio', 'com.system76.CosmicAppletBluetooth',
              'com.system76.CosmicAppletNetwork', 'com.system76.CosmicAppletBattery',
              'com.system76.CosmicAppletNotifications', 'com.system76.CosmicAppletTime',
              'com.system76.CosmicAppletPower'],
}

def panel_text(key):
    path = PANEL / key
    if not path.exists(): path = SYSTEM_PANEL / key
    return path.read_text()

def strings(text):
    return [json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', text)]

def panel_layout():
    text = panel_text('plugins_wings')
    match = re.fullmatch(r'\s*Some\(\(\s*\[(.*?)\]\s*,\s*\[(.*?)\]\s*,?\s*\)\)\s*', text, re.S)
    if not match:
        if text.strip() == 'None': left, right = [], []
        else: raise ValueError('Could not read the current panel layout.')
    else: left, right = (strings(part) for part in match.groups())
    return {'left': left, 'right': right, 'center': strings(panel_text('plugins_center'))}

def read_values():
    def read(key, default):
        try: return (CONFIG/key).read_text().strip()
        except FileNotFoundError: return default
    values = dict(appearance.DEFAULTS)
    for key in values:
        try: values[key] = json.loads(read(key, appearance.encode(values[key])))
        except (ValueError, TypeError): pass
    try: values = appearance.normalize(values)
    except (ValueError, TypeError): values = dict(appearance.DEFAULTS)
    try: threshold = max(1, min(50, int(read('group_after', '5'))))
    except ValueError: threshold = 5
    return {**values, 'grouping_enabled': read('grouping_enabled', 'true') == 'true',
            'group_after': threshold,
            'only_current_output': read('only_current_output', 'true') == 'true'}

def read_panel_style():
    result = dict(appearance.PANEL_MXWL)
    for key in result:
        try: raw = panel_text(key).strip()
        except FileNotFoundError: continue
        if key == 'background':
            if raw == 'ThemeDefault': result[key] = raw
            elif raw.startswith('Color('):
                channels = re.findall(r'[0-9]+(?:\.[0-9]+)?', raw)
                if len(channels) == 3:
                    result[key] = '#%02x%02x%02x' % tuple(max(0, min(255, round(float(c)*255))) for c in channels)
        elif key == 'size': result[key] = raw
        else:
            try: result[key] = round(float(raw) * (100 if key == 'opacity' else 1))
            except ValueError: pass
    return result

def backup(paths):
    dest = Path.home()/'.local/state/cosmic-backups'/datetime.datetime.now().strftime('window-list-settings-%Y%m%d-%H%M%S-%f')
    for path in paths:
        if path.exists():
            target = dest/path.relative_to(Path.home())
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

def save(values, visibility=None, panel_style=None):
    values = {**read_values(), **values}
    values.update(appearance.normalize(values))
    values['group_after'] = max(1, min(50, int(values['group_after'])))
    keys = ['grouping_enabled', 'group_after', 'only_current_output', *appearance.DEFAULTS]
    paths = [CONFIG/k for k in keys]
    panel_changes = appearance.panel_values(panel_style) if panel_style is not None else {}
    paths += [PANEL/k for k in panel_changes]
    layout = panel_layout() if visibility is not None else None
    if layout is not None:
        paths += [PANEL/'plugins_wings', PANEL/'plugins_center']
        for _, ident, wing in ICONS:
            enabled = visibility[ident]
            if not enabled:
                for items in layout.values():
                    items[:] = [item for item in items if item != ident]
            elif not any(ident in items for items in layout.values()):
                order = ORDER[wing]
                index = next((i for i, item in enumerate(layout[wing])
                              if item in order and order.index(item) > order.index(ident)), len(layout[wing]))
                layout[wing].insert(index, ident)
    backup(paths)
    CONFIG.mkdir(parents=True, exist_ok=True)
    for key in keys:
        value = values[key]
        path = CONFIG/key
        text = appearance.encode(value)
        if not path.exists() or path.read_text() != text:
            path.write_text(text)
    if panel_changes:
        PANEL.mkdir(parents=True, exist_ok=True)
        for key, text in panel_changes.items():
            if panel_text(key).strip() != text.strip(): (PANEL/key).write_text(text)
    if layout is not None:
        PANEL.mkdir(parents=True, exist_ok=True)
        wings = 'Some((' + json.dumps(layout['left']) + ', ' + json.dumps(layout['right']) + '))\n'
        center = 'Some(' + json.dumps(layout['center']) + ')\n'
        # Avoid restarting all applets when only window-list options changed.
        if panel_text('plugins_wings').strip() != wings.strip(): (PANEL/'plugins_wings').write_text(wings)
        if strings(panel_text('plugins_center')) != layout['center']: (PANEL/'plugins_center').write_text(center)

def apply_defaults(*, panel_defaults=True):
    CONFIG.mkdir(parents=True, exist_ok=True)
    for key, value in [('filter_top_levels','None'), ('favorites','[]'), ('enable_drag_source','true'),
                       ('grouping_enabled','true'), ('group_after','5'), ('only_current_output','true')]:
        path=CONFIG/key
        if not path.exists(): path.write_text(value+'\n')
    for key, value in appearance.DEFAULTS.items():
        path = CONFIG/key
        if not path.exists(): path.write_text(appearance.encode(value))
    marker=CONFIG/'panel_defaults_applied'
    if panel_defaults and not marker.exists():
        save(read_values(), {ident: False for _,ident,_ in ICONS})
        marker.write_text('true\n')

def run_gui():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gio, Gdk
    app=Gtk.Application(application_id='io.github.kerry.CosmicWindowListSettings', flags=Gio.ApplicationFlags.FLAGS_NONE)
    def activate(application):
        existing=application.get_active_window()
        if existing:
            existing.present(); return
        values=read_values()
        layout=panel_layout()
        win=Gtk.ApplicationWindow(application=application, title='Window List Settings')
        win.set_default_size(600, 720)
        win.set_border_width(22)
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        win.add(outer)
        notebook=Gtk.Notebook();outer.pack_start(notebook,True,True,0)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(16)
        notebook.append_page(box,Gtk.Label(label='Windows & panel icons'))
        style_page, read_style=appearance.build_ui(Gtk,Gdk,values,read_panel_style())
        notebook.append_page(style_page,Gtk.Label(label='Appearance'))
        title=Gtk.Label(xalign=0)
        title.set_markup('<big><b>Window List</b></big>')
        box.pack_start(title,False,False,0)
        group=Gtk.CheckButton(label='Combine windows of the same app')
        group.set_active(values['grouping_enabled']);box.pack_start(group,False,False,0)
        row=Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label='Keep up to', xalign=0),False,False,0)
        threshold=Gtk.SpinButton.new_with_range(1,50,1)
        threshold.set_value(values['group_after']);row.pack_start(threshold,False,False,0)
        row.pack_start(Gtk.Label(label='windows separate'),False,False,0)
        box.pack_start(row,False,False,0)
        explanation=Gtk.Label(xalign=0)
        explanation.set_line_wrap(True)
        box.pack_start(explanation,False,False,0)
        def threshold_changed(*_):
            n=threshold.get_value_as_int()
            explanation.set_text(f'Window {n+1} combines that app into one button. Click it to pick a window.')
            row.set_sensitive(group.get_active())
        threshold.connect('value-changed',threshold_changed)
        group.connect('toggled',threshold_changed);threshold_changed()
        monitor=Gtk.CheckButton(label='Only show windows on this monitor')
        monitor.set_active(values['only_current_output']);box.pack_start(monitor,False,False,0)
        hint=Gtk.Label(label='Each panel shows the windows on its own screen.',xalign=0)
        box.pack_start(hint,False,False,0)
        box.pack_start(Gtk.Separator(),False,False,2)
        heading=Gtk.Label(xalign=0);heading.set_markup('<b>Show these panel icons</b>')
        box.pack_start(heading,False,False,0)
        grid=Gtk.Grid(column_spacing=24,row_spacing=8)
        checks={}
        for i,(label,ident,_) in enumerate(ICONS):
            checkbox=Gtk.CheckButton(label=label)
            checkbox.set_active(any(ident in items for items in layout.values()))
            grid.attach(checkbox,i%2,i//2,1,1);checks[ident]=checkbox
        box.pack_start(grid,False,False,0)
        status=Gtk.Label(xalign=0);status.set_line_wrap(True)
        outer.pack_end(status,False,False,0)
        actions=Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        actions.set_layout(Gtk.ButtonBoxStyle.END)
        close=Gtk.Button(label='Close');close.connect('clicked',lambda _:win.destroy());actions.add(close)
        apply=Gtk.Button(label='Apply');apply.get_style_context().add_class('suggested-action');actions.add(apply)
        def apply_clicked(_):
            try:
                style,panel_style=read_style()
                save({**style, 'grouping_enabled':group.get_active(), 'group_after':threshold.get_value_as_int(),
                      'only_current_output':monitor.get_active()},
                     {ident:checkbox.get_active() for ident,checkbox in checks.items()},panel_style)
                status.set_text('Saved. Your panels update immediately.')
            except Exception as error:
                status.set_text('Could not save settings: '+str(error))
        apply.connect('clicked',apply_clicked)
        outer.pack_end(actions,False,False,0)
        win.show_all()
    app.connect('activate',activate)
    app.run([])

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-defaults',action='store_true')
    parser.add_argument('--preset',choices=('mxwl','system'))
    parser.add_argument('--panel',action='store_true',help='Also apply the mxwl panel colors and dimensions.')
    parser.add_argument('--show',action='store_true',help='Print current values as JSON.')
    args=parser.parse_args()
    if args.apply_defaults: apply_defaults()
    elif args.show: print(json.dumps({'windows':read_values(),'panel':read_panel_style()},indent=2))
    elif args.preset:
        save(appearance.MXWL if args.preset=='mxwl' else appearance.DEFAULTS,
             panel_style=appearance.PANEL_MXWL if args.panel else None)
        print('Applied '+args.preset+' appearance.')
    else: run_gui()
