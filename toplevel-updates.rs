use crate::wayland_subscription::ToplevelUpdate;
use cctk::{
    toplevel_info::ToplevelInfo,
    wayland_protocols::ext::foreign_toplevel_list::v1::client::ext_foreign_toplevel_handle_v1::ExtForeignToplevelHandleV1,
};
use std::collections::HashMap;

/// Keep title animations from submitting a new panel frame for every tick.
#[derive(Default)]
pub(crate) struct ToplevelUpdates {
    last_sent: HashMap<ExtForeignToplevelHandleV1, ToplevelInfo>,
}

impl ToplevelUpdates {
    pub(crate) fn filter(&mut self, update: ToplevelUpdate) -> Option<ToplevelUpdate> {
        match update {
            ToplevelUpdate::Add(mut info) => {
                stabilize_title(&mut info.title);
                self.last_sent
                    .insert(info.foreign_toplevel.clone(), info.clone());
                Some(ToplevelUpdate::Add(info))
            }
            ToplevelUpdate::Update(mut info) => {
                stabilize_title(&mut info.title);
                if self
                    .last_sent
                    .get(&info.foreign_toplevel)
                    .is_some_and(|previous| same_info(previous, &info))
                {
                    return None;
                }
                self.last_sent
                    .insert(info.foreign_toplevel.clone(), info.clone());
                Some(ToplevelUpdate::Update(info))
            }
            ToplevelUpdate::Remove(handle) => {
                self.last_sent.remove(&handle);
                Some(ToplevelUpdate::Remove(handle))
            }
        }
    }
}

fn stabilize_title(title: &mut String) {
    // Codex and other terminal tools prefix titles with this braille spinner.
    // Keep a static busy indicator; only recognize a complete leading token so
    // ordinary braille text and symbols elsewhere in a title stay untouched.
    let Some((prefix, _)) = title.split_once(' ') else {
        return;
    };
    if matches!(prefix, "⠋" | "⠙" | "⠹" | "⠸" | "⠼" | "⠴" | "⠦" | "⠧" | "⠇" | "⠏") {
        title.replace_range(..prefix.len(), "…");
    }
}

fn same_info(a: &ToplevelInfo, b: &ToplevelInfo) -> bool {
    a.title == b.title
        && a.app_id == b.app_id
        && a.identifier == b.identifier
        && a.foreign_toplevel == b.foreign_toplevel
        && a.cosmic_toplevel == b.cosmic_toplevel
        && a.state == b.state
        && a.output == b.output
        && a.workspace == b.workspace
        && a.geometry.len() == b.geometry.len()
        && a.geometry.iter().all(|(output, geometry)| {
            b.geometry.get(output).is_some_and(|other| {
                (geometry.x, geometry.y, geometry.width, geometry.height)
                    == (other.x, other.y, other.width, other.height)
            })
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use cctk::{
        toplevel_info::ToplevelGeometry,
        wayland_client::{Connection, Proxy, protocol::wl_output::WlOutput},
        wayland_protocols::ext::workspace::v1::client::ext_workspace_handle_v1::ExtWorkspaceHandleV1,
    };
    use cosmic_protocols::toplevel_info::v1::client::zcosmic_toplevel_handle_v1::State;
    use std::os::unix::net::UnixStream;

    fn info(title: &str) -> ToplevelInfo {
        let (socket, _server) = UnixStream::pair().unwrap();
        let connection = Connection::from_socket(socket).unwrap();
        ToplevelInfo {
            title: title.into(),
            app_id: "test.terminal".into(),
            identifier: "test-window".into(),
            foreign_toplevel: ExtForeignToplevelHandleV1::inert(connection.backend().downgrade()),
            cosmic_toplevel: None,
            state: Default::default(),
            output: Default::default(),
            workspace: Default::default(),
            geometry: Default::default(),
        }
    }

    #[test]
    fn spinner_ticks_do_not_reach_the_ui() {
        let mut updates = ToplevelUpdates::default();
        let mut window = info("⠋ Working | project");
        let Some(ToplevelUpdate::Add(added)) = updates.filter(ToplevelUpdate::Add(window.clone()))
        else {
            panic!("new window must be forwarded");
        };
        assert_eq!(added.title, "… Working | project");
        for frame in "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏".chars().cycle().take(100) {
            window.title = format!("{frame} Working | project");
            assert!(
                updates
                    .filter(ToplevelUpdate::Update(window.clone()))
                    .is_none()
            );
        }
        for title in ["⠙ Another task | project", "Done | project", "⠋ Done | project"] {
            window.title = title.into();
            assert!(
                updates
                    .filter(ToplevelUpdate::Update(window.clone()))
                    .is_some()
            );
        }
    }

    #[test]
    fn ordinary_titles_are_preserved() {
        for original in [
            "", "Terminal", "⠋", "⠋braille", "Text ⠋ spinner", "日本語 🦀", "⠃ braille",
        ] {
            let mut title = original.to_string();
            stabilize_title(&mut title);
            assert_eq!(title, original);
        }
    }

    #[test]
    fn state_and_location_changes_are_immediate_during_animation() {
        let mut updates = ToplevelUpdates::default();
        let mut window = info("⠋ Working");
        updates.filter(ToplevelUpdate::Add(window.clone()));
        let backend = window.foreign_toplevel.backend().clone();
        let output = WlOutput::inert(backend.clone());
        let workspace = ExtWorkspaceHandleV1::inert(backend);
        // Each change accompanies a spinner tick, as it can on the desktop.
        for change in 0..8 {
            window.title = "⠙ Working".into();
            match change {
                0 => {
                    window.state.insert(State::Activated);
                }
                1 => {
                    window.state.insert(State::Minimized);
                }
                2 => {
                    window.state.remove(&State::Activated);
                }
                3 => {
                    window.output.insert(output.clone());
                }
                4 => {
                    window.workspace.insert(workspace.clone());
                }
                5 => {
                    window.geometry.insert(output.clone(), ToplevelGeometry {
                        x: 10, y: 20, width: 800, height: 600,
                    });
                }
                6 => {
                    window.geometry.get_mut(&output).unwrap().x += 1;
                }
                7 => {
                    window.app_id = "another.app".into();
                }
                _ => unreachable!(),
            }
            assert!(
                updates.filter(ToplevelUpdate::Update(window.clone())).is_some(),
                "change {change}"
            );
            assert!(
                updates.filter(ToplevelUpdate::Update(window.clone())).is_none()
            );
        }
    }

    #[test]
    fn closing_forgets_the_cached_window() {
        let mut updates = ToplevelUpdates::default();
        let window = info("⠋ Working");
        updates.filter(ToplevelUpdate::Add(window.clone()));
        assert!(
            updates
                .filter(ToplevelUpdate::Remove(window.foreign_toplevel.clone()))
                .is_some()
        );
        assert!(updates.last_sent.is_empty());
        assert!(updates.filter(ToplevelUpdate::Add(window)).is_some());
    }
}
