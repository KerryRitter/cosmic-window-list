#!/usr/bin/env python3
"""Install a built applet and replace App Tray in the existing panel only."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import shlex
import importlib.util
import argparse

parser = argparse.ArgumentParser(description='Install COSMIC Window List for the current user.')
parser.add_argument('--no-enable', action='store_true',
                    help='Install files without changing panel layout or panel icon visibility.')
parser.add_argument('--preserve-panel-icons', action='store_true',
                    help='Enable/reload the applet without applying first-install panel icon defaults.')
args = parser.parse_args()

project = Path(__file__).resolve().parent
binary = project / "upstream/target/release/cosmic-window-list"
if not binary.is_file():
    raise SystemExit("No built executable. Run bash build.sh successfully first.")
home = Path.home()
panel = home / ".config/cosmic/com.system76.CosmicPanel.Panel/v1"
paths = [panel / "plugins_wings", panel / "plugins_center"]
old, new = '"com.system76.CosmicAppList"', '"io.github.kerry.CosmicWindowList"'
found = [p for p in paths if p.exists() and (old in p.read_text() or new in p.read_text())]
if not found and not args.no_enable:
    raise SystemExit("App Tray not found in your panel. Run with --no-enable, then add Window List in COSMIC Settings → Desktop → Panel.")
# Check desktop access before making any changes.
if not args.no_enable:
    subprocess.run(["busctl", "--user", "list", "--no-pager"],
                   check=True, stdout=subprocess.DEVNULL)
backup = home / ".local/state/cosmic-backups" / datetime.datetime.now().strftime("before-window-list-%Y%m%d-%H%M%S-%f")
backup.mkdir(parents=True)
manifest = {}
for p in ([] if args.no_enable else found):
    rel = str(p.relative_to(home))
    dest = backup / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
    manifest[rel] = True
(backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
installed = home / ".local/bin/cosmic-window-list"
installed.parent.mkdir(parents=True, exist_ok=True)
staged = installed.with_suffix(".new")
shutil.copy2(binary, staged)
staged.chmod(0o755)
staged.replace(installed)
settings_file = home / '.local/share/cosmic-window-list/settings.py'
settings_file.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(project/'settings.py', settings_file)
shutil.copy2(project/'appearance.py', settings_file.with_name('appearance.py'))
settings_launcher = home / '.local/bin/cosmic-window-list-settings'
settings_launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(settings_file))+' "$@"\n')
settings_launcher.chmod(0o755)
settings_desktop = home / '.local/share/applications/io.github.kerry.CosmicWindowListSettings.desktop'
settings_desktop.parent.mkdir(parents=True, exist_ok=True)
settings_desktop.write_text(f'''[Desktop Entry]
Name=Window List Settings
Comment=Style window buttons and panel colors, grouping, monitor filtering, and icons
Type=Application
Exec={settings_launcher}
Icon=preferences-system
Terminal=false
Categories=Settings;DesktopSettings;
''')
spec=importlib.util.spec_from_file_location('window_list_settings',settings_file)
settings=importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)
settings.apply_defaults(panel_defaults=not (args.no_enable or args.preserve_panel_icons))
desktop = home / ".local/share/applications/io.github.kerry.CosmicWindowList.desktop"
desktop.parent.mkdir(parents=True, exist_ok=True)
desktop.write_text(f'''[Desktop Entry]
Name=Window List
Comment=Window buttons with adjustable grouping. Right-click for settings.
Type=Application
Exec={installed}
Icon=com.system76.CosmicAppList
Terminal=false
NoDisplay=true
Categories=COSMIC;
X-CosmicApplet=true
X-CosmicHoverPopup=Auto
X-HostWaylandDisplay=true
X-OverflowPriority=100
X-OverflowMinSize=4
X-MinimizeApplet=5
''')
for p in ([] if args.no_enable else found):
    contents = p.read_text()
    if new in contents:
        # COSMIC does not respawn applets on a clean exit. Switch this slot
        # through the stock applet so a rebuild is loaded reliably.
        p.write_text(contents.replace(new, old))
        time.sleep(0.6)
    p.write_text(contents.replace(old, new))
if args.no_enable:
    print('Installed. Add Window List in COSMIC Settings → Desktop → Panel → applets.')
else:
    print(f"Installed and selected applet. Backup: {backup}")
    print("If COSMIC has not refreshed the panel, log out and back in.")
