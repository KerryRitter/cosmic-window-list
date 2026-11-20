                PopupType::WindowMenu(handle) => {
                    let Some((info, _)) = toplevels.iter()
                        .find(|(info, _)| &info.foreign_toplevel == handle) else {
                        return text::body("").into();
                    };
                    let menu_button = |label: &'static str| button::custom(text::body(label))
                        .height(20 + 2 * theme::spacing().space_xxs)
                        .class(Button::MenuItem)
                        .padding(menu_control_padding())
                        .width(Length::Fill);
                    let mut content = menu::menu_column::MenuColumn::with_capacity(6);
                    let minimized = info.state.contains(&State::Minimized);
                    content = content.push(menu_button(if minimized { "Restore" } else { "Focus" })
                        .on_press(Message::WindowMenuAction(ToplevelRequest::Activate(handle.clone()))));
                    if !minimized {
                        content = content.push(menu_button("Minimize")
                            .on_press(Message::WindowMenuAction(ToplevelRequest::Minimize(handle.clone()))));
                    }
                    content = content.push(divider::horizontal::light());
                    content = content.push(menu_button("Close window")
                        .on_press(Message::WindowMenuAction(ToplevelRequest::Quit(handle.clone()))));
                    content = content.push(divider::horizontal::light());
                    content = content.push(menu_button("Window List Settings…")
                        .on_press(Message::Exec(format!("{}/.local/bin/cosmic-window-list-settings",
                            std::env::var("HOME").unwrap_or_default()), None, false)));
                    self.core.applet.popup_container(
                        container(content).padding(1).height(Length::Shrink).width(Length::Fill)
                    ).limits(Limits::NONE.min_width(200.0).max_width(300.0).max_height(1000.0)).into()
                }
