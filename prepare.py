#!/usr/bin/env python3
"""Generate an independent applet from the pinned upstream source."""
import argparse
from pathlib import Path
import subprocess
import appearance

APP_ID = 'io.github.kerry.CosmicWindowList'
BASE = Path(__file__).resolve().parent

def original(root, path):
    return subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:' + path], text=True)

def prepare(root):
    path = 'cosmic-app-list/src/app.rs'
    source = original(root, path)
    source = source.replace('.and_then(|c| AppListConfig::get_entry(&c).ok())',
                            '.map(|c| AppListConfig::get_entry(&c).unwrap_or_else(|(_, config)| config))', 1)
    source = source.replace('enum Message {', 'enum Message {\n    ScrollWindows(f32),', 1)
    source = source.replace('        match message {', '''        match message {
            Message::ScrollWindows(x) => {
                return cosmic::iced::widget::scrollable::scroll_by(
                    cosmic::widget::Id::new("window-list-scroll"),
                    cosmic::iced::widget::scrollable::AbsoluteOffset { x, y: 0.0 },
                );
            }
''', 1)
    marker = '    fn is_on_current_monitor_and_workspace(&self, toplevel_info: &ToplevelInfo) -> bool {'
    assert source.count(marker) == 1
    source = source.replace(marker, marker + '''
        if self.config.only_current_output {
            let matches_output = self.output_list.iter().any(|(output, info)| {
                info.name.as_ref() == Some(&self.core.applet.output_name)
                    && toplevel_info.output.contains(output)
            });
            if !matches_output { return false; }
        }
''', 1)
    start = source.index("    fn view(&self) -> Element<'_, Message> {")
    end = source.index("    fn view_window(&self, id: window::Id) -> Element<'_, Message> {", start)
    source = source[:start] + (BASE / 'window-list-view.rs').read_text() + '\n' + source[end:]
    source += '\n' + (BASE / 'window-list-style.rs').read_text()
    marker = "    fn view_window(&self, id: window::Id) -> Element<'_, Message> {"
    source = source.replace(marker, marker + '\n' + (BASE / 'group-popup.rs').read_text(), 1)
    # Use the upstream anchored popup lifecycle, with a compact scrolling list.
    group_start = source.index('            Message::ToplevelListPopup(id, parent_window_id) => {')
    copy_start = source.index('                    for (info, _) in &toplevel_group.toplevels {', group_start)
    copy_end = source.index('                    let Some(rectangle)', copy_start)
    source = source[:copy_start] + source[copy_end:]
    size_start = source.index('                                let max_windows = 7.0;', group_start)
    size_end = source.index('\n                                popup_settings\n', size_start)
    source = source[:size_start] + '''                                popup_settings.positioner.size_limits = Limits::NONE
                                    .min_width(240.0).max_width(420.0)
                                    .min_height(36.0).max_height(480.0);
''' + source[size_end:]
    (root / path).write_text(source)

    # Avoid submitting extra frames for duplicate protocol notifications.
    module_path = 'cosmic-app-list/src/lib.rs'
    module = original(root, module_path)
    marker = 'mod wayland_handler;'
    assert module.count(marker) == 1
    (root / module_path).write_text(module.replace(marker, 'mod toplevel_updates;\n' + marker, 1))
    (root / 'cosmic-app-list/src/toplevel_updates.rs').write_text((BASE / 'toplevel-updates.rs').read_text())
    handler_path = 'cosmic-app-list/src/wayland_handler.rs'
    handler = original(root, handler_path)
    marker = '    toplevel_info_state: ToplevelInfoState,'
    assert handler.count(marker) == 1
    handler = handler.replace(marker, marker + '\n    toplevel_updates: crate::toplevel_updates::ToplevelUpdates,', 1)
    marker = '        toplevel_info_state: ToplevelInfoState::new(&registry_state, &qh),'
    assert handler.count(marker) == 1
    handler = handler.replace(marker, marker + '\n        toplevel_updates: Default::default(),', 1)
    marker = '// Workspace and toplevel handling'
    assert handler.count(marker) == 1
    handler = handler.replace(marker, '''impl AppData {
    fn send_toplevel_update(&mut self, update: ToplevelUpdate) {
        if let Some(update) = self.toplevel_updates.filter(update) {
            let _ = self.tx.unbounded_send(WaylandUpdate::Toplevel(update));
        }
    }
}

''' + marker, 1)
    replacements = [
        ('''            let _ = self
                .tx
                .unbounded_send(WaylandUpdate::Toplevel(ToplevelUpdate::Add(info.clone())));''',
         '            self.send_toplevel_update(ToplevelUpdate::Add(info.clone()));'),
        ('''            let _ = self
                .tx
                .unbounded_send(WaylandUpdate::Toplevel(ToplevelUpdate::Update(
                    info.clone(),
                )));''',
         '            self.send_toplevel_update(ToplevelUpdate::Update(info.clone()));'),
        ('''        let _ = self
            .tx
            .unbounded_send(WaylandUpdate::Toplevel(ToplevelUpdate::Remove(
                toplevel.clone(),
            )));''',
         '        self.send_toplevel_update(ToplevelUpdate::Remove(toplevel.clone()));'),
    ]
    for before, after in replacements:
        assert handler.count(before) == 1
        handler = handler.replace(before, after, 1)
    (root / handler_path).write_text(handler)

    config_path = 'cosmic-app-list/cosmic-app-list-config/src/lib.rs'
    cfg = original(root, config_path).replace('com.system76.CosmicAppList', APP_ID)
    cfg = cfg.replace('    pub enable_drag_source: bool,', '''    pub enable_drag_source: bool,
    pub grouping_enabled: bool,
    pub group_after: u32,
    pub only_current_output: bool,''', 1)
    cfg = cfg.replace('            enable_drag_source: true,', '''            enable_drag_source: true,
            grouping_enabled: true,
            group_after: 5,
            only_current_output: true,''', 1)
    fields = []
    defaults = []
    for key, value in appearance.DEFAULTS.items():
        rust_type = 'bool' if isinstance(value, bool) else 'u32' if isinstance(value, int) else 'String'
        fields.append(f'    pub {key}: {rust_type},')
        literal = appearance.encode(value).strip()
        if isinstance(value, str): literal += '.to_owned()'
        defaults.append(f'            {key}: {literal},')
    cfg = cfg.replace('    pub only_current_output: bool,', '    pub only_current_output: bool,\n' + '\n'.join(fields), 1)
    cfg = cfg.replace('            only_current_output: true,', '            only_current_output: true,\n' + '\n'.join(defaults), 1)
    (root / config_path).write_text(cfg)
    binary = root / 'cosmic-app-list/src/bin/cosmic-window-list.rs'
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text('''fn main() -> cosmic::iced::Result {
    tracing_subscriber::fmt::init();
    let _ = tracing_log::LogTracer::init();
    tracing::info!("Starting COSMIC Window List");
    cosmic_app_list::run()
}
''')
    print('Prepared COSMIC Window List with settings, threshold grouping and output filtering.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('checkout', type=Path)
    prepare(parser.parse_args().checkout)
