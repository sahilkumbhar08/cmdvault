# cmdvault/themes.py
"""
Light and Dark theme configuration for CmdVault.
Central source for colors, fonts, and spacing. Fedora-friendly, high-contrast.
"""

# Spacing (pixels) — consistent 8–12px
PAD = 10
PAD_SM = 8
PAD_LG = 12

# Font families
FONT_SANS = "Sans"
FONT_MONO = "Courier New"

# Light theme (default)
LIGHT = {
    "bg": "#f8f9fa",
    "fg": "#1a1d21",
    "sidebar_bg": "#e9ecef",
    "sidebar_fg": "#212529",
    "sidebar_hover_bg": "#dee2e6",
    "sidebar_select_bg": "#e9ecef",
    "sidebar_accent": "#0d6efd",
    "entry_bg": "#ffffff",
    "entry_fg": "#1a1d21",
    "entry_border": "#ced4da",
    "entry_placeholder_fg": "#6c757d",
    "card_bg": "#ffffff",
    "card_fg": "#1a1d21",
    "card_border": "#dee2e6",
    "card_shadow": "#e9ecef",
    "listbox_bg": "#ffffff",
    "listbox_fg": "#1a1d21",
    "listbox_select_bg": "#cfe2ff",
    "listbox_select_fg": "#052c65",
    "button_bg": "#e9ecef",
    "button_fg": "#212529",
    "button_hover_bg": "#dee2e6",
    "button_active_bg": "#ced4da",
    "accent_bg": "#0d6efd",
    "accent_fg": "#ffffff",
    "accent_hover_bg": "#0b5ed7",
    "status_bg": "#e9ecef",
    "status_fg": "#495057",
    "status_success_bg": "#d1e7dd",
    "status_success_fg": "#0f5132",
}

# Dark theme
DARK = {
    "bg": "#212529",
    "fg": "#e9ecef",
    "sidebar_bg": "#1a1d21",
    "sidebar_fg": "#e9ecef",
    "sidebar_hover_bg": "#2d3238",
    "sidebar_select_bg": "#252a30",
    "sidebar_accent": "#4dabf7",
    "entry_bg": "#343a40",
    "entry_fg": "#e9ecef",
    "entry_border": "#495057",
    "entry_placeholder_fg": "#868e96",
    "card_bg": "#343a40",
    "card_fg": "#e9ecef",
    "card_border": "#495057",
    "card_shadow": "#252a30",
    "listbox_bg": "#343a40",
    "listbox_fg": "#e9ecef",
    "listbox_select_bg": "#36404a",
    "listbox_select_fg": "#ffffff",
    "button_bg": "#495057",
    "button_fg": "#e9ecef",
    "button_hover_bg": "#5c636a",
    "button_active_bg": "#6c757d",
    "accent_bg": "#339af0",
    "accent_fg": "#ffffff",
    "accent_hover_bg": "#4dabf7",
    "status_bg": "#1a1d21",
    "status_fg": "#adb5bd",
    "status_success_bg": "#2b4a2e",
    "status_success_fg": "#75b798",
}


def get_theme(dark: bool) -> dict:
    """Return theme dict for dark=True or dark=False."""
    base = DARK if dark else LIGHT
    out = dict(base)
    out["font_title"] = (FONT_SANS, 11, "bold")
    out["font_command"] = (FONT_MONO, 10)
    out["font_ui"] = (FONT_SANS, 10)
    return out
