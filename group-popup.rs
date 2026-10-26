        if let Some(popup) = self.popup.as_ref().filter(|p| p.id == id && p.popup_type == PopupType::ToplevelList) {
            // Look up the live group, so titles and membership update while open.
            if let Some(item) = self.active_list.iter().chain(self.pinned_list.iter())
                .find(|item| item.id == popup.dock_item.id) {
                let mut rows = column![].spacing(4);
                for (info, _) in item.toplevels.iter()
                    .filter(|(info, _)| self.is_on_current_monitor_and_workspace(info)) {
                    let activate = button::custom(text::body(info.title.clone())
                        .size(self.config.font_size.clamp(9, 24) as u16)
                        .font(window_list_font(&self.config))
                        .ellipsize(Ellipsize::End(EllipsizeHeightLimit::Lines(1))))
                        .padding(10).width(Length::Fill)
                        .class(window_list_style(&self.config, info.state.contains(&State::Activated)))
                        .on_press(Message::Activate(info.foreign_toplevel.clone()));
                    let close = button::custom(icon::from_name("window-close-symbolic").size(16))
                        .padding(8).class(Button::AppletMenu)
                        .on_press(Message::CloseToplevel(info.foreign_toplevel.clone()));
                    rows = rows.push(row![activate, close].spacing(4).align_y(Alignment::Center));
                }
                return self.core.applet.popup_container(
                    cosmic::widget::scrollable(rows).width(Length::Fixed(380.0)).height(Length::Shrink)
                ).limits(Limits::NONE.min_width(240.0).max_width(420.0).max_height(480.0)).into();
            }
        }
