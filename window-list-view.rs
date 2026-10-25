    fn view(&self) -> Element<'_, Message> {
        // Filter first so the threshold applies to the windows on THIS panel.
        let mut entries: Vec<(&DockItem, Vec<&ToplevelInfo>)> = Vec::new();
        for item in self.active_list.iter().chain(self.pinned_list.iter()) {
            let visible: Vec<_> = item.toplevels.iter()
                .map(|(info, _)| info)
                .filter(|info| self.is_on_current_monitor_and_workspace(info))
                .collect();
            if self.config.grouping_enabled && visible.len() > self.config.group_after.max(1) as usize {
                entries.push((item, visible));
            } else {
                for info in visible { entries.push((item, vec![info])); }
            }
        }
        let horizontal = self.core.applet.is_horizontal();
        let bounds = self.core.applet.suggested_bounds;
        let available = bounds.map(|b| if horizontal { b.width } else { b.height })
            .filter(|n| n.is_finite() && *n > 0.0).unwrap_or(900.0);
        let button_width = ((available - entries.len() as f32 * 2.0)
            / entries.len().max(1) as f32).clamp(72.0, 200.0);
        let settings = Message::Exec(format!("{}/.local/bin/cosmic-window-list-settings",
            std::env::var("HOME").unwrap_or_default()), None, false);
        let mut buttons: Vec<Element<'_, Message>> = Vec::new();
        for (item, windows) in entries {
            let grouped = windows.len() > 1;
            let focused = windows.iter().any(|info| info.state.contains(&State::Activated));
            let info = windows[0];
            let label = if grouped {
                let name = item.desktop_info.full_name(&self.locales)
                    .map(|n| n.into_owned()).unwrap_or_else(|| info.app_id.clone());
                format!("{} ({})", name, windows.len())
            } else if info.title.is_empty() { info.app_id.clone() } else { info.title.clone() };
            let action = if grouped {
                Message::ToplevelListPopup(item.id, self.core.main_window_id().unwrap())
            } else { Message::Toggle(info.foreign_toplevel.clone()) };
            let content = row![
                cosmic::widget::icon(fde::IconSource::from_unknown(
                    item.desktop_info.icon().unwrap_or_default()).as_cosmic_icon()).size(20),
                text::body(label.clone())
                    .ellipsize(Ellipsize::End(EllipsizeHeightLimit::Lines(1)))
                    .width(Length::Fill),
            ].spacing(6).align_y(Alignment::Center);
            let btn = button::custom(content)
                .padding([4, 6])
                .width(Length::Fixed(if horizontal { button_width } else { 180.0 }))
                .selected(focused).class(app_list_icon_style(focused)).on_press(action.clone());
            let middle = if grouped { action } else { Message::CloseToplevel(info.foreign_toplevel.clone()) };
            let btn = mouse_area(btn).on_middle_release(middle).on_right_release(settings.clone());
            let btn = if horizontal {
                btn.on_scroll(|delta| Message::ScrollWindows(match delta {
                    cosmic::iced::mouse::ScrollDelta::Lines { x, y } => -(x + y) * 60.0,
                    cosmic::iced::mouse::ScrollDelta::Pixels { x, y } => -(x + y),
                }))
            } else { btn };
            let btn: Element<'_, Message> = if grouped {
                if let Some(tracker) = self.rectangle_tracker.as_ref() {
                    tracker.container(item.id.into(), btn).into()
                } else { btn.into() }
            } else { btn.into() };
            buttons.push(self.core.applet.applet_tooltip::<Message>(
                btn, label, self.popup.is_some(), Message::Surface, None,
            ).into());
        }
        if buttons.is_empty() {
            buttons.push(mouse_area(text::body("No windows")).on_right_release(settings).into());
        }
        let content: Element<'_, Message> = if horizontal {
            cosmic::widget::scrollable(row(buttons).spacing(2).align_y(Alignment::Center))
                .id(cosmic::widget::Id::new("window-list-scroll"))
                .direction(cosmic::iced::widget::scrollable::Direction::Horizontal(
                    cosmic::iced::widget::scrollable::Scrollbar::default(),
                )).width(Length::Shrink).into()
        } else {
            cosmic::widget::scrollable(column(buttons).spacing(2)).height(Length::Shrink).into()
        };
        let mut limits = Limits::NONE.min_width(1.0).min_height(1.0);
        if let Some(b) = bounds {
            if b.width > 0.0 { limits = limits.max_width(b.width); }
            if b.height > 0.0 { limits = limits.max_height(b.height); }
        }
        self.core.applet.autosize_window(container(content)).limits(limits).into()
    }
