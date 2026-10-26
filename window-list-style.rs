// Appearance values are copied into closures so config changes redraw immediately.
fn window_list_style(config: &AppListConfig, selected: bool) -> cosmic::theme::Button {
    if !config.custom_style { return app_list_icon_style(selected); }
    use cosmic::iced::Color;
    fn color(value: &str, fallback: Color) -> Color {
        value.strip_prefix('#').filter(|s| s.len() == 6)
            .and_then(|s| u32::from_str_radix(s, 16).ok())
            .map(|n| Color::from_rgb8((n >> 16) as u8, (n >> 8) as u8, n as u8))
            .unwrap_or(fallback)
    }
    let normal = color(&config.button_background, Color::from_rgb8(37, 37, 38));
    let hover = color(&config.hover_background, Color::from_rgb8(45, 45, 48));
    let active = color(&config.active_background, Color::from_rgb8(41, 49, 38));
    let text = color(if selected { &config.active_text_color } else { &config.text_color }, Color::WHITE);
    let border = color(if selected { &config.accent_color } else { &config.border_color }, Color::TRANSPARENT);
    let style = button::Style {
        background: Some(Background::Color(if selected { active } else { normal })),
        text_color: Some(text), icon_color: Some(text),
        border_radius: (config.corner_radius.min(24) as f32).into(),
        border_width: config.border_width.min(4) as f32, border_color: border,
        outline_width: 0.0, ..button::Style::default()
    };
    let hovered = button::Style { background: Some(Background::Color(hover)), ..style };
    Button::Custom {
        active: Box::new(move |_, _| style),
        hovered: Box::new(move |_, _| hovered),
        pressed: Box::new(move |_, _| button::Style { background: Some(Background::Color(active)), ..style }),
        disabled: Box::new(move |_| style),
    }
}

fn window_list_font(config: &AppListConfig) -> cosmic::iced::Font {
    use cosmic::iced::font::Family;
    match config.font_family.as_str() {
        "IBM Plex Mono" => cosmic::iced::Font { family: Family::Name("IBM Plex Mono"), ..Default::default() },
        "Space Grotesk" => cosmic::iced::Font { family: Family::Name("Space Grotesk"), ..Default::default() },
        "Monospace" => cosmic::iced::Font::MONOSPACE,
        _ => cosmic::config::interface_font().into(),
    }
}
