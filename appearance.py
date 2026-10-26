"""Appearance schema shared by the settings UI and generated Rust config."""
import json
import re

# Integers keep the COSMIC config comparable and avoid invalid float geometry.
NUMBERS = {
    'button_min_width': (72, 32, 400), 'button_max_width': (200, 32, 600),
    'font_size': (14, 9, 24), 'icon_size': (20, 12, 32),
    'button_gap': (2, 0, 24), 'padding_x': (6, 0, 24),
    'padding_y': (4, 0, 16), 'corner_radius': (4, 0, 24),
    'border_width': (1, 0, 4),
}
COLORS = {
    'button_background': '#252526', 'hover_background': '#2d2d30',
    'active_background': '#293126', 'text_color': '#e0e0e0',
    'active_text_color': '#a2cc90', 'accent_color': '#91bd7d',
    'border_color': '#454545',
}
DEFAULTS = {**{k: v[0] for k, v in NUMBERS.items()}, **COLORS,
            'custom_style': False, 'show_icons': True, 'show_titles': True,
            'font_family': 'System'}
MXWL = {**DEFAULTS, 'custom_style': True, 'button_min_width': 100,
        'button_max_width': 240, 'font_size': 14, 'icon_size': 16,
        'button_gap': 2, 'padding_x': 6, 'padding_y': 2,
        'corner_radius': 0, 'font_family': 'IBM Plex Mono'}
PANEL_MXWL = {'background': '#1e1e1e', 'opacity': 100, 'size': 'XS',
              'border_radius': 0, 'padding': 0, 'spacing': 2}


def accent_colors(accent, background='#1e1e1e'):
    """Derive all active colors from one machine or applet accent."""
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
        raise ValueError('Accent must be a six-digit hex color, e.g. #8ccfe5.')
    def channels(color): return tuple(int(color[i:i+2],16) for i in (1,3,5))
    rgb=channels(accent); base=channels(background)
    def mix(left,right,amount):
        return '#%02x%02x%02x' % tuple(round(a+(b-a)*amount) for a,b in zip(left,right))
    return {'accent_color':accent.lower(), 'active_text_color':mix(rgb,(255,255,255),.25),
            'active_background':mix(base,rgb,.12)}


def normalize(values):
    result = {**DEFAULTS, **{k: v for k, v in values.items() if k in DEFAULTS}}
    for key, (_, low, high) in NUMBERS.items():
        result[key] = max(low, min(high, int(result[key])))
    if result['button_min_width'] > result['button_max_width']:
        raise ValueError('Minimum button width must not exceed maximum width.')
    for key in COLORS:
        if not isinstance(result[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', result[key]):
            raise ValueError(f'{key.replace("_", " ")} must be a six-digit hex color.')
        result[key] = result[key].lower()
    for key in ('custom_style', 'show_icons', 'show_titles'):
        if not isinstance(result[key], bool):
            raise ValueError(f'{key} must be true or false.')
    if not result['show_icons'] and not result['show_titles']:
        raise ValueError('Show icons or window titles so buttons remain identifiable.')
    if result['font_family'] not in ('System', 'Space Grotesk', 'IBM Plex Mono', 'Monospace'):
        raise ValueError('Choose a supported font family.')
    return result


def encode(value):
    return json.dumps(value, ensure_ascii=False) + '\n'


def panel_values(values):
    """Validate UI values before producing native COSMIC panel RON."""
    color = values['background']
    if color != 'ThemeDefault' and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Panel background must be a hex color or ThemeDefault.')
    if values['size'] not in ('XS', 'S', 'M', 'L', 'XL'):
        raise ValueError('Invalid panel size.')
    result = {'background': 'ThemeDefault' if color == 'ThemeDefault' else
              'Color((' + ', '.join(f'{int(color[i:i+2], 16)/255:.8f}' for i in (1, 3, 5)) + '))',
              'size': values['size']}
    for key, high in (('opacity', 100), ('border_radius', 100), ('padding', 32), ('spacing', 32)):
        value = int(values[key])
        if not 0 <= value <= high:
            raise ValueError(f'Panel {key} must be between 0 and {high}.')
        result[key] = str(value / 100) if key == 'opacity' else str(value)
    return {k: v + '\n' for k, v in result.items()}


def build_ui(Gtk, Gdk, values, panel):
    """Return a scrollable appearance page and a validated value reader."""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    page.set_border_width(16)
    presets = Gtk.Box(spacing=8)
    presets.pack_start(Gtk.Label(label='Preset', xalign=0), False, False, 0)
    system = Gtk.Button(label='System'); mxwl = Gtk.Button(label='mxwl')
    presets.pack_start(system, False, False, 0); presets.pack_start(mxwl, False, False, 0)
    page.pack_start(presets, False, False, 0)
    widgets = {}
    for key, label in (('custom_style', 'Use custom button colors and borders'),
                       ('show_icons', 'Show application icons'), ('show_titles', 'Show window titles')):
        widget = Gtk.CheckButton(label=label); widget.set_active(values[key]); widgets[key] = widget
        page.pack_start(widget, False, False, 0)
    grid = Gtk.Grid(column_spacing=18, row_spacing=8)
    page.pack_start(grid, False, False, 0)
    def field(label, widget):
        row = len(widgets)
        grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
        grid.attach(widget, 1, row, 1, 1)
    font = Gtk.ComboBoxText()
    for name in ('System', 'Space Grotesk', 'IBM Plex Mono', 'Monospace'): font.append(name, name)
    font.set_active_id(values['font_family']); field('Font', font); widgets['font_family'] = font
    labels={'font_size':'Label font size', 'icon_size':'Application icon size',
            'button_gap':'Gap between tiles', 'padding_x':'Tile horizontal padding',
            'padding_y':'Tile vertical padding'}
    for key, (_, low, high) in NUMBERS.items():
        widget = Gtk.SpinButton.new_with_range(low, high, 1); widget.set_value(values[key])
        field(labels.get(key,key.replace('_', ' ').capitalize()), widget); widgets[key] = widget
    color_labels={'button_background':'Background color', 'text_color':'Foreground color',
                  'hover_background':'Hover background color', 'active_background':'Active background color',
                  'active_text_color':'Active foreground color', 'accent_color':'Accent color',
                  'border_color':'Border color'}
    for key in ('button_background','text_color','hover_background','active_background',
                'active_text_color','accent_color','border_color'):
        rgba = Gdk.RGBA(); rgba.parse(values[key])
        widget = Gtk.ColorButton.new_with_rgba(rgba); widget.set_use_alpha(False)
        widget.set_title(color_labels[key])
        field(color_labels[key], widget); widgets[key] = widget
    def accent_changed(widget):
        rgba=widget.get_rgba()
        accent='#%02x%02x%02x' % tuple(round(v*255) for v in (rgba.red,rgba.green,rgba.blue))
        for key,color in accent_colors(accent).items():
            if key!='accent_color':
                rgba=Gdk.RGBA();rgba.parse(color);widgets[key].set_rgba(rgba)
    widgets['accent_color'].connect('color-set',accent_changed)
    preview = Gtk.Box(spacing=8)
    normal_preview=Gtk.Label(label='Window title'); normal_preview.set_name('window-list-normal-preview')
    active_preview=Gtk.Label(label='mxwl-editor'); active_preview.set_name('window-list-active-preview')
    preview.pack_start(normal_preview,True,True,0); preview.pack_start(active_preview,True,True,0)
    provider=Gtk.CssProvider()
    for widget in (normal_preview,active_preview):
        widget.get_style_context().add_provider(provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    page.pack_start(preview, False, False, 0)
    def read():
        result = {}
        for key, widget in widgets.items():
            if key in NUMBERS: result[key] = widget.get_value_as_int()
            elif key in COLORS:
                rgba = widget.get_rgba()
                result[key] = '#%02x%02x%02x' % tuple(round(v*255) for v in (rgba.red, rgba.green, rgba.blue))
            elif key == 'font_family': result[key] = widget.get_active_id()
            else: result[key] = widget.get_active()
        return normalize(result)
    def update_preview(*_):
        try: style = read()
        except ValueError: return
        font=style['font_family'] if style['font_family']!='System' else 'sans-serif'
        css=''
        for name,active in (('normal',False),('active',True)):
            css+=f'''#window-list-{name}-preview {{
                background-color: {style['active_background' if active else 'button_background']};
                color: {style['active_text_color' if active else 'text_color']};
                border: {style['border_width']}px solid {style['accent_color' if active else 'border_color']};
                border-radius: {style['corner_radius']}px;
                padding: {style['padding_y']}px {style['padding_x']}px;
                font-family: "{font}"; font-size: {style['font_size']}px;
            }}'''
        provider.load_from_data(css.encode())
    for key, widget in widgets.items():
        widget.connect('value-changed' if key in NUMBERS else 'color-set' if key in COLORS else
                       'changed' if key == 'font_family' else 'toggled', update_preview)
    update_preview()
    hint = Gtk.Label(label='Preview shows normal and active colors. Apply to see exact panel geometry.\n'
                     'Accent color also updates the active tile text and background.\n'
                     'Use mxwl OS Appearance to change the accent across this machine.', xalign=0)
    hint.set_line_wrap(True); page.pack_start(hint, False, False, 0)
    from gi.repository import Gio
    machine_app=Gio.DesktopAppInfo.new('io.github.kerry.MxwlOSAppearance.desktop')
    if machine_app:
        machine_button=Gtk.Button(label='Machine accent…')
        machine_button.connect('clicked',lambda _:machine_app.launch([],None))
        page.pack_start(machine_button,False,False,0)
    panel_enable = Gtk.CheckButton(label='Also update the panel background and dimensions')
    page.pack_start(panel_enable, False, False, 0)
    panel_grid = Gtk.Grid(column_spacing=18, row_spacing=8)
    page.pack_start(panel_grid, False, False, 0)
    panel_widgets = {}
    for i, (key, value) in enumerate(panel.items()):
        if key == 'background':
            widget=Gtk.Box(spacing=8)
            entry=Gtk.Entry();entry.set_text(value);entry.set_width_chars(14)
            color=Gdk.RGBA();color.parse(value if value!='ThemeDefault' else '#1e1e1e')
            picker=Gtk.ColorButton.new_with_rgba(color);picker.set_use_alpha(False)
            picker.set_title('Panel background color')
            def pick_background(button):
                color=button.get_rgba()
                entry.set_text('#%02x%02x%02x' % tuple(round(v*255) for v in (color.red,color.green,color.blue)))
            def type_background(text):
                color=Gdk.RGBA()
                if color.parse(text.get_text()):picker.set_rgba(color)
            picker.connect('color-set',pick_background);entry.connect('changed',type_background)
            widget.pack_start(picker,False,False,0);widget.pack_start(entry,False,False,0)
            widget.get_text=entry.get_text
        elif key == 'size':
            widget = Gtk.ComboBoxText()
            for size,name in (('XS','Smallest'),('S','Small'),('M','Medium'),('L','Large'),('XL','Largest')):
                widget.append(size,size+' — '+name)
            widget.set_active_id(value)
        else:
            widget = Gtk.SpinButton.new_with_range(0, 100 if key in ('opacity', 'border_radius') else 32, 1)
            widget.set_value(value)
        label='Panel height' if key=='size' else 'Panel background color' if key=='background' else 'Panel '+key.replace('_', ' ')
        panel_grid.attach(Gtk.Label(label=label, xalign=0), 0, i, 1, 1)
        panel_grid.attach(widget, 1, i, 1, 1); panel_widgets[key] = widget
    panel_grid.set_sensitive(False)
    panel_enable.connect('toggled', lambda w: panel_grid.set_sensitive(w.get_active()))
    def preset(style):
        for key, widget in widgets.items():
            if key in NUMBERS: widget.set_value(style[key])
            elif key in COLORS:
                rgba = Gdk.RGBA(); rgba.parse(style[key]); widget.set_rgba(rgba)
            elif key == 'font_family': widget.set_active_id(style[key])
            else: widget.set_active(style[key])
        update_preview()
    system.connect('clicked', lambda _: preset(DEFAULTS))
    mxwl.connect('clicked', lambda _: preset({**MXWL,**accent_colors(read()['accent_color'])}))
    def get_values():
        panel_style = None
        if panel_enable.get_active():
            panel_style = {k: w.get_text() if k == 'background' else w.get_active_id() if k == 'size'
                           else w.get_value_as_int() for k, w in panel_widgets.items()}
            panel_values(panel_style)
        return read(), panel_style
    scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(page)
    return scroll, get_values
