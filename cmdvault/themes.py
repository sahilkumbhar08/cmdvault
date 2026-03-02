# cmdvault/themes.py
"""
Developer Tool aesthetic: Slate/Zinc dark theme.
Inter for UI, JetBrains Mono for code. Fallbacks for systems without these fonts.
"""

# Spacing (pixels)
PAD = 10
PAD_SM = 8
PAD_LG = 12
RADIUS = 8  # Card corner radius (visual; Tk has no native rounded rects)

# Typography: Inter (labels), JetBrains Mono (commands). Tk falls back if missing.
FONT_SANS = "Inter"
FONT_MONO = "JetBrains Mono"

# Developer Dark (Slate/Zinc) — primary theme
DEV_DARK = {
    "bg": "#09090b",
    "fg": "#fafafa",
    "border": "#27272a",
    "sidebar_bg": "#18181b",
    "sidebar_fg": "#a1a1aa",
    "sidebar_hover_bg": "#27272a",
    "sidebar_select_bg": "#27272a",
    "sidebar_accent": "#6366f1",
    "entry_bg": "#18181b",
    "entry_fg": "#fafafa",
    "entry_border": "#27272a",
    "entry_placeholder_fg": "#71717a",
    "card_bg": "#18181b",
    "card_fg": "#fafafa",
    "card_border": "#27272a",
    "card_shadow": "#09090b",
    "listbox_bg": "#18181b",
    "listbox_fg": "#fafafa",
    "listbox_select_bg": "#27272a",
    "listbox_select_fg": "#a5b4fc",
    "button_bg": "transparent",
    "button_fg": "#a1a1aa",
    "button_hover_bg": "#27272a",
    "button_active_bg": "#3f3f46",
    "accent_bg": "#6366f1",
    "accent_fg": "#ffffff",
    "accent_hover_bg": "#4f46e5",
    "status_bg": "#18181b",
    "status_fg": "#71717a",
    "status_success_bg": "#064e3b",
    "status_success_fg": "#10b981",
    "success": "#10b981",
    "danger": "#ef4444",
    "tab_active_fg": "#6366f1",
    "tab_inactive_fg": "#71717a",
}

# Light theme (kept for View → Dark Mode toggle off)
LIGHT = {
    "bg": "#fafafa",
    "fg": "#18181b",
    "border": "#e4e4e7",
    "sidebar_bg": "#f4f4f5",
    "sidebar_fg": "#18181b",
    "sidebar_hover_bg": "#e4e4e7",
    "sidebar_select_bg": "#e4e4e7",
    "sidebar_accent": "#6366f1",
    "entry_bg": "#ffffff",
    "entry_fg": "#18181b",
    "entry_border": "#e4e4e7",
    "entry_placeholder_fg": "#71717a",
    "card_bg": "#ffffff",
    "card_fg": "#18181b",
    "card_border": "#e4e4e7",
    "card_shadow": "#f4f4f5",
    "listbox_bg": "#ffffff",
    "listbox_fg": "#18181b",
    "listbox_select_bg": "#e0e7ff",
    "listbox_select_fg": "#4338ca",
    "button_bg": "transparent",
    "button_fg": "#52525b",
    "button_hover_bg": "#e4e4e7",
    "button_active_bg": "#d4d4d8",
    "accent_bg": "#6366f1",
    "accent_fg": "#ffffff",
    "accent_hover_bg": "#4f46e5",
    "status_bg": "#f4f4f5",
    "status_fg": "#52525b",
    "status_success_bg": "#d1fae5",
    "status_success_fg": "#059669",
    "success": "#10b981",
    "danger": "#ef4444",
    "tab_active_fg": "#6366f1",
    "tab_inactive_fg": "#71717a",
}

# Legacy DARK alias (map to DEV_DARK)
DARK = DEV_DARK


def get_theme(dark: bool) -> dict:
    """Return theme dict. Uses DEV_DARK when dark=True."""
    base = DEV_DARK if dark else LIGHT
    out = dict(base)
    out["font_title"] = (FONT_SANS, 11, "bold")
    out["font_command"] = (FONT_MONO, 10)
    out["font_ui"] = (FONT_SANS, 10)
    out["font_mono"] = (FONT_MONO, 10)
    return out
