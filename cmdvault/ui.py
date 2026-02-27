# cmdvault/ui.py
"""
Modern UI for CmdVault: ttk-themed sidebar, card-based command list,
search bar with placeholder, status bar, double-click to copy.
"""

import json
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Optional
from . import db as db_module
from .themes import get_theme, PAD, PAD_SM, PAD_LG
from .utils import copy_to_clipboard, filter_commands_fuzzy

SEARCH_PLACEHOLDER = "Search commands…"
CMD_PREVIEW_LEN = 80


def _truncate(s: str, max_len: int = CMD_PREVIEW_LEN) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


# --- Dialogs ---

class CommandDialog(simpledialog.Dialog):
    """Modal dialog to add or edit a command: Title + Command + Category."""

    def __init__(self, parent, title: str, categories: list, initial_title: str = "",
                 initial_command: str = "", initial_category_id: Optional[int] = None):
        self.categories = categories
        self.initial_title = initial_title
        self.initial_command = initial_command
        self.initial_category_id = initial_category_id
        self.result_tuple: Optional[tuple] = None
        super().__init__(parent, title)

    def body(self, master):
        master.winfo_toplevel().lift()
        ttk.Label(master, text="Title:").grid(row=0, column=0, sticky="w", padx=PAD, pady=PAD_SM)
        self.title_var = tk.StringVar(value=self.initial_title)
        self.title_entry = ttk.Entry(master, textvariable=self.title_var, width=42)
        self.title_entry.grid(row=0, column=1, padx=PAD, pady=PAD_SM)

        ttk.Label(master, text="Command:").grid(row=1, column=0, sticky="nw", padx=PAD, pady=PAD_SM)
        self.cmd_text = tk.Text(master, width=42, height=5, relief=tk.FLAT, padx=4, pady=4)
        self.cmd_text.insert("1.0", self.initial_command)
        self.cmd_text.grid(row=1, column=1, padx=PAD, pady=PAD_SM)

        ttk.Label(master, text="Category:").grid(row=2, column=0, sticky="w", padx=PAD, pady=PAD_SM)
        self.cat_var = tk.StringVar()
        names = [c["name"] for c in self.categories]
        self.cat_combo = ttk.Combobox(master, textvariable=self.cat_var, values=names, state="readonly", width=39)
        self.cat_combo.grid(row=2, column=1, padx=PAD, pady=PAD_SM)
        if self.categories:
            if self.initial_category_id:
                for c in self.categories:
                    if c["id"] == self.initial_category_id:
                        self.cat_var.set(c["name"])
                        break
            if not self.cat_var.get():
                self.cat_var.set(names[0])
        return self.title_entry

    def apply(self):
        title = self.title_var.get().strip()
        command = self.cmd_text.get("1.0", "end-1c").strip()
        cat_name = (self.cat_var.get() or "").strip()
        if not cat_name and self.categories:
            cat_name = self.categories[0]["name"]
        if not title:
            messagebox.showwarning("Validation", "Title is required.", parent=self)
            return
        if not command:
            messagebox.showwarning("Validation", "Command is required.", parent=self)
            return
        category_id = None
        for c in self.categories:
            if c["name"] == cat_name:
                category_id = c["id"]
                break
        if category_id is None:
            messagebox.showwarning("Validation", "Please select a category.", parent=self)
            return
        self.result_tuple = (title, command, category_id)


class SecretDialog(simpledialog.Dialog):
    """Modal dialog to add or edit a secret: Title + Secret key + Description (optional)."""

    def __init__(self, parent, dialog_title: str, initial_title: str = "",
                 initial_secret: str = "", initial_description: str = ""):
        self.initial_title = initial_title
        self.initial_secret = initial_secret or ""
        self.initial_description = initial_description or ""
        self.result_tuple: Optional[tuple] = None
        super().__init__(parent, dialog_title)

    def body(self, master):
        master.winfo_toplevel().lift()
        ttk.Label(master, text="Title:").grid(row=0, column=0, sticky="w", padx=PAD, pady=PAD_SM)
        self.title_var = tk.StringVar(value=self.initial_title)
        self.title_entry = ttk.Entry(master, textvariable=self.title_var, width=42)
        self.title_entry.grid(row=0, column=1, padx=PAD, pady=PAD_SM)

        ttk.Label(master, text="Secret key:").grid(row=1, column=0, sticky="w", padx=PAD, pady=PAD_SM)
        secret_frame = ttk.Frame(master)
        secret_frame.grid(row=1, column=1, sticky="w", padx=PAD, pady=PAD_SM)
        self.secret_var = tk.StringVar(value=self.initial_secret)
        self.secret_entry = tk.Entry(secret_frame, textvariable=self.secret_var, width=36, show="*")
        self.secret_entry.pack(side=tk.LEFT)
        self._secret_visible = False
        self.show_btn = ttk.Button(secret_frame, text="Show", width=6, command=self._toggle_secret)
        self.show_btn.pack(side=tk.LEFT, padx=(PAD_SM, 0))

        ttk.Label(master, text="Description (optional):").grid(row=2, column=0, sticky="nw", padx=PAD, pady=PAD_SM)
        self.desc_text = tk.Text(master, width=42, height=4, relief=tk.FLAT, padx=4, pady=4)
        self.desc_text.insert("1.0", self.initial_description)
        self.desc_text.grid(row=2, column=1, padx=PAD, pady=PAD_SM)
        return self.title_entry

    def _toggle_secret(self) -> None:
        self._secret_visible = not self._secret_visible
        self.secret_entry.configure(show="" if self._secret_visible else "*")
        self.show_btn.configure(text="Hide" if self._secret_visible else "Show")

    def apply(self):
        title = self.title_var.get().strip()
        secret = (self.secret_var.get() or "").strip()
        description = self.desc_text.get("1.0", "end-1c").strip()
        if not title:
            messagebox.showwarning("Validation", "Title is required.", parent=self)
            return
        if not secret:
            messagebox.showwarning("Validation", "Secret key is required.", parent=self)
            return
        self.result_tuple = (title, secret, description or None)


class CategoryDialog(simpledialog.Dialog):
    """Modal dialog to add a category."""

    def __init__(self, parent, title: str = "Add Category"):
        self.result_name: Optional[str] = None
        super().__init__(parent, title)

    def body(self, master):
        master.winfo_toplevel().lift()
        ttk.Label(master, text="Category name:").grid(row=0, column=0, sticky="w", padx=PAD, pady=PAD)
        self.name_var = tk.StringVar()
        self.entry = ttk.Entry(master, textvariable=self.name_var, width=32)
        self.entry.grid(row=0, column=1, padx=PAD, pady=PAD)
        return self.entry

    def apply(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Category name is required.", parent=self)
            return
        self.result_name = name


# --- Main UI ---

class CmdVaultUI:
    """Main application UI: sidebar, search, command cards, status bar. Double-click row to copy."""

    SIDEBAR_WIDTH = 220

    def __init__(self, root: tk.Tk, conn):
        self.root = root
        self.conn = conn
        self.dark_mode = self._load_dark_mode()
        self.theme = get_theme(self.dark_mode)
        self.selected_category_id: Optional[int] = None
        self._command_rows: list = []
        self._category_list: list = []
        self._selected_command_index: Optional[int] = None
        self._command_cards_frame: Optional[tk.Frame] = None
        self._card_widgets: list = []
        self._secrets_frame: Optional[tk.Frame] = None
        self._secret_rows: list = []
        self._status_is_success = False

        root.title("CmdVault")
        root.minsize(720, 480)
        root.geometry("960x580")

        self._configure_styles()
        self._build_menus()
        self._build_layout()
        self._apply_theme(self.theme)
        self._bind_shortcuts()

        self.refresh_categories()
        self.refresh_commands()
        self.refresh_secrets()
        self._select_first_category_if_any()

    def _load_dark_mode(self) -> bool:
        val = db_module.get_setting(self.conn, "dark_mode")
        return val == "1"

    def _save_dark_mode(self, dark: bool) -> None:
        db_module.set_setting(self.conn, "dark_mode", "1" if dark else "0")

    def _configure_styles(self) -> None:
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("TFrame", background=self.theme["bg"])
        self.style.configure("TLabel", background=self.theme["bg"], foreground=self.theme["fg"], padding=(PAD_SM, PAD_SM))
        self.style.configure("TButton", padding=(PAD, PAD_SM))
        self.style.configure("TEntry", padding=(PAD_SM, PAD_SM))
        self.style.configure("Sidebar.TFrame", background=self.theme["sidebar_bg"])
        self.style.configure("Sidebar.TLabel", background=self.theme["sidebar_bg"], foreground=self.theme["sidebar_fg"], padding=(PAD, PAD_SM))
        self.style.configure("Accent.TButton", background=self.theme["accent_bg"], foreground=self.theme["accent_fg"], padding=(PAD, PAD_SM))
        accent_hover = self.theme["accent_hover_bg"]
        self.style.map("Accent.TButton", background=[("active", accent_hover), ("pressed", accent_hover)])
        self.style.configure("Placeholder.TLabel", foreground=self.theme["entry_placeholder_fg"], padding=(PAD_SM, 0))

    def _build_menus(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        view_menu.add_checkbutton(label="Dark Mode", variable=self.dark_mode_var, command=self._toggle_dark_mode)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import from file...", command=self._import_from_file)
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")

    def _toggle_dark_mode(self) -> None:
        self.dark_mode = self.dark_mode_var.get()
        self._save_dark_mode(self.dark_mode)
        self.theme = get_theme(self.dark_mode)
        self._apply_theme(self.theme)

    def _import_from_file(self) -> None:
        """Import commands and secrets from a JSON file. See import_sample.json for format."""
        path = filedialog.askopenfilename(
            title="Import from JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            messagebox.showerror("Import failed", f"Invalid JSON: {e}", parent=self.root)
            return
        except OSError as e:
            messagebox.showerror("Import failed", f"Cannot read file: {e}", parent=self.root)
            return
        name_to_id = {c["name"]: c["id"] for c in db_module.list_categories(self.conn)}
        n_commands = 0
        n_secrets = 0
        for cat_name in data.get("categories") or []:
            cat_name = (cat_name or "").strip()
            if cat_name and cat_name not in name_to_id:
                try:
                    name_to_id[cat_name] = db_module.add_category(self.conn, cat_name)
                except sqlite3.IntegrityError:
                    name_to_id[cat_name] = next(c["id"] for c in db_module.list_categories(self.conn) if c["name"] == cat_name)
        for item in data.get("commands") or []:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            command = (item.get("command") or "").strip()
            cat_name = (item.get("category") or "general").strip()
            if not title:
                continue
            if cat_name not in name_to_id:
                try:
                    name_to_id[cat_name] = db_module.add_category(self.conn, cat_name)
                except sqlite3.IntegrityError:
                    name_to_id[cat_name] = next((c["id"] for c in db_module.list_categories(self.conn) if c["name"] == cat_name), name_to_id.get("general", 1))
            try:
                db_module.add_command(self.conn, title, command, name_to_id[cat_name])
                n_commands += 1
            except Exception:
                pass
        for item in data.get("secrets") or []:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            secret = (item.get("secret") or "").strip()
            description = (item.get("description") or "").strip() or None
            if not title or not secret:
                continue
            try:
                db_module.add_secret(self.conn, title, secret, description)
                n_secrets += 1
            except Exception:
                pass
        self.refresh_categories()
        self.refresh_commands()
        self.refresh_secrets()
        self.status_var.set(f"Import done: {n_commands} command(s), {n_secrets} secret(s).")
        messagebox.showinfo("Import", f"Imported {n_commands} command(s) and {n_secrets} secret(s).", parent=self.root)

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=PAD)
        main.pack(fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(main)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # --- Tab 1: Commands ---
        tab_commands = ttk.Frame(self._notebook, padding=0)
        self._notebook.add(tab_commands, text="Commands")
        cmd_main = ttk.Frame(tab_commands)
        cmd_main.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(cmd_main, width=self.SIDEBAR_WIDTH, style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PAD_LG))
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="Categories", style="Sidebar.TLabel").pack(anchor="w", padx=PAD, pady=(0, PAD_SM))
        ttk.Button(sidebar, text="➕ Add Category", command=self._add_category, style="Accent.TButton").pack(fill=tk.X, padx=PAD, pady=(0, PAD_SM))
        cat_list_frame = ttk.Frame(sidebar)
        cat_list_frame.pack(fill=tk.BOTH, expand=True)
        self._cat_canvas = tk.Canvas(cat_list_frame, highlightthickness=0, bg=self.theme["sidebar_bg"])
        cat_scroll = ttk.Scrollbar(cat_list_frame)
        self.cat_inner = tk.Frame(self._cat_canvas, bg=self.theme["sidebar_bg"])
        self.cat_inner.bind("<Configure>", lambda e: self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all")))
        self._cat_canvas.create_window((0, 0), window=self.cat_inner, anchor="nw")
        self._cat_canvas.configure(yscrollcommand=cat_scroll.set)
        cat_scroll.config(command=self._cat_canvas.yview)
        self._cat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._category_frames: list = []
        ttk.Button(sidebar, text="Delete Category", command=self._delete_category).pack(fill=tk.X, padx=PAD, pady=PAD_SM)

        right = ttk.Frame(cmd_main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_container = ttk.Frame(right)
        search_container.pack(fill=tk.X, pady=(0, PAD_LG))
        ttk.Label(search_container, text="🔍 Search").pack(side=tk.LEFT, padx=(0, PAD))
        search_inner = ttk.Frame(search_container)
        search_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search_change())
        self.search_entry = ttk.Entry(search_inner, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, ipady=PAD_SM, ipadx=PAD_SM)
        self._search_placeholder = ttk.Label(search_inner, text=SEARCH_PLACEHOLDER, style="Placeholder.TLabel")
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)
        self._search_placeholder.bind("<Button-1>", lambda e: self._search_placeholder_click())
        self._search_placeholder.place(in_=self.search_entry, relx=0.02, rely=0, relwidth=0.96, relheight=1)

        cards_container = ttk.Frame(right)
        cards_container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(cards_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(cards_container)
        self._command_cards_frame = tk.Frame(canvas)
        self._command_cards_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._command_cards_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.config(command=canvas.yview)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._cards_canvas = canvas

        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X, pady=PAD)
        ttk.Button(btn_frame, text="➕ Add Command", command=self._add_command, style="Accent.TButton").pack(side=tk.LEFT)

        # --- Tab 2: Secrets (permanent "Secret key" section) ---
        tab_secrets = ttk.Frame(self._notebook, padding=PAD)
        self._notebook.add(tab_secrets, text="Secrets")
        ttk.Label(tab_secrets, text="Secret key", font=self.theme["font_title"]).pack(anchor="w", pady=(0, PAD))
        ttk.Button(tab_secrets, text="➕ Add Secret", command=self._add_secret, style="Accent.TButton").pack(anchor="w", pady=(0, PAD))
        secrets_scroll = ttk.Frame(tab_secrets)
        secrets_scroll.pack(fill=tk.BOTH, expand=True)
        sec_canvas = tk.Canvas(secrets_scroll, highlightthickness=0)
        sec_scrollbar = ttk.Scrollbar(secrets_scroll)
        self._secrets_frame = tk.Frame(sec_canvas)
        self._secrets_frame.bind("<Configure>", lambda e: sec_canvas.configure(scrollregion=sec_canvas.bbox("all")))
        sec_canvas.create_window((0, 0), window=self._secrets_frame, anchor="nw")
        sec_canvas.configure(yscrollcommand=sec_scrollbar.set)
        sec_scrollbar.config(command=sec_canvas.yview)
        sec_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sec_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._secrets_canvas = sec_canvas

        # Status bar (shared)
        self._status_frame = tk.Frame(main, relief=tk.FLAT)
        self._status_frame.pack(fill=tk.X, pady=(PAD, 0))
        self.status_var = tk.StringVar(value="Ready")
        self._status_label = tk.Label(self._status_frame, textvariable=self.status_var, anchor="w", font=self.theme["font_ui"])
        self._status_label.pack(fill=tk.X, padx=PAD, pady=PAD_SM)

    def _search_focus_in(self, event) -> None:
        self._search_placeholder.place_forget()

    def _search_placeholder_click(self) -> None:
        self._search_placeholder.place_forget()
        self.search_entry.focus_set()

    def _search_focus_out(self, event) -> None:
        if not self.search_var.get().strip():
            self._search_placeholder.place(in_=self.search_entry, relx=0.02, rely=0, relwidth=0.96, relheight=1)

    def _on_search_change(self) -> None:
        if self.search_var.get().strip():
            self._search_placeholder.place_forget()
        self.refresh_commands()

    def _get_search_query(self) -> str:
        return self.search_var.get().strip()

    def _apply_theme(self, theme: dict) -> None:
        self.theme = theme
        self.root.configure(bg=theme["bg"])
        self.style.configure("TFrame", background=theme["bg"])
        self.style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        self.style.configure("Sidebar.TFrame", background=theme["sidebar_bg"])
        self.style.configure("Sidebar.TLabel", background=theme["sidebar_bg"], foreground=theme["sidebar_fg"])
        self.style.configure("Accent.TButton", background=theme["accent_bg"], foreground=theme["accent_fg"])
        self.style.map("Accent.TButton", background=[("active", theme["accent_hover_bg"]), ("pressed", theme["accent_hover_bg"])])
        self.style.configure("Placeholder.TLabel", foreground=theme["entry_placeholder_fg"])
        self._cards_canvas.configure(bg=theme["bg"])
        if hasattr(self, "_secrets_canvas"):
            self._secrets_canvas.configure(bg=theme["bg"])
        if hasattr(self, "_secrets_frame"):
            self._secrets_frame.configure(bg=theme["bg"])
        if hasattr(self, "_cat_canvas"):
            self._cat_canvas.configure(bg=theme["sidebar_bg"])
        if hasattr(self, "cat_inner"):
            self.cat_inner.configure(bg=theme["sidebar_bg"])
        for i, (f, accent, lbl) in enumerate(self._category_frames):
            is_selected = (self.selected_category_id is not None and i < len(self._category_list) and
                          self._category_list[i]["id"] == self.selected_category_id)
            f.configure(bg=theme["sidebar_select_bg"] if is_selected else theme["sidebar_bg"])
            accent.configure(bg=theme["sidebar_accent"] if is_selected else theme["sidebar_bg"])
            lbl.configure(bg=f["bg"], fg=theme["sidebar_fg"])
        self._update_status_style()
        self.refresh_commands()
        self.refresh_secrets()

    def _update_status_style(self) -> None:
        if self._status_is_success:
            self._status_frame.configure(bg=self.theme["status_success_bg"])
            self._status_label.configure(bg=self.theme["status_success_bg"], fg=self.theme["status_success_fg"])
        else:
            self._status_frame.configure(bg=self.theme["status_bg"])
            self._status_label.configure(bg=self.theme["status_bg"], fg=self.theme["status_fg"])

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-n>", lambda e: self._add_command())
        self.root.bind("<Control-Shift-N>", lambda e: self._add_category())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-F>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<Return>", lambda e: self._copy_selected())
        self.root.bind("<Control-c>", lambda e: self._copy_selected())

    def _on_category_select(self, index: int) -> None:
        if 0 <= index < len(self._category_list):
            self.selected_category_id = self._category_list[index]["id"]
        else:
            self.selected_category_id = None
        self._refresh_category_visuals()
        self.refresh_commands()

    def _refresh_category_visuals(self) -> None:
        for i, (f, accent, lbl) in enumerate(self._category_frames):
            is_selected = (self.selected_category_id is not None and i < len(self._category_list) and
                          self._category_list[i]["id"] == self.selected_category_id)
            f.configure(bg=self.theme["sidebar_select_bg"] if is_selected else self.theme["sidebar_bg"])
            accent.configure(bg=self.theme["sidebar_accent"] if is_selected else self.theme["sidebar_bg"])
            lbl.configure(bg=f["bg"])

    def _select_first_category_if_any(self) -> None:
        if self._category_list:
            self.selected_category_id = self._category_list[0]["id"]
            self._refresh_category_visuals()
            self.refresh_commands()

    def refresh_categories(self) -> None:
        self._category_list = db_module.list_categories(self.conn)
        for w in self.cat_inner.winfo_children():
            w.destroy()
        self._category_frames.clear()
        for i, c in enumerate(self._category_list):
            is_selected = self.selected_category_id == c["id"]
            row = tk.Frame(self.cat_inner, bg=self.theme["sidebar_select_bg"] if is_selected else self.theme["sidebar_bg"], cursor="hand2")
            accent = tk.Frame(row, width=4, bg=self.theme["sidebar_accent"] if is_selected else self.theme["sidebar_bg"])
            accent.pack(side=tk.LEFT, fill=tk.Y)
            lbl = tk.Label(row, text=c["name"], font=self.theme["font_ui"], bg=row["bg"], fg=self.theme["sidebar_fg"], anchor="w", padx=PAD, pady=PAD_SM)
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            row.pack(fill=tk.X, pady=1)
            idx = i
            for w in (row, accent, lbl):
                w.bind("<Button-1>", lambda e, i=idx: self._on_category_select(i))
                w.bind("<Enter>", lambda e, r=row, a=accent: self._cat_enter(r, a))
                w.bind("<Leave>", lambda e, r=row, a=accent: self._cat_leave(r, a))
            self._category_frames.append((row, accent, lbl))

    def _cat_enter(self, row: tk.Frame, accent: tk.Frame) -> None:
        if self.selected_category_id is None or not any(
            self._category_list[j]["id"] == self.selected_category_id
            for j, (r, *_) in enumerate(self._category_frames) if r == row
        ):
            row.configure(bg=self.theme["sidebar_hover_bg"])
            accent.configure(bg=self.theme["sidebar_hover_bg"])

    def _cat_leave(self, row: tk.Frame, accent: tk.Frame) -> None:
        for j, (r, a, _) in enumerate(self._category_frames):
            if r == row:
                is_selected = self._category_list[j]["id"] == self.selected_category_id
                row.configure(bg=self.theme["sidebar_select_bg"] if is_selected else self.theme["sidebar_bg"])
                accent.configure(bg=self.theme["sidebar_accent"] if is_selected else self.theme["sidebar_bg"])
                break

    def refresh_commands(self) -> None:
        raw = db_module.list_commands(self.conn, category_id=self.selected_category_id)
        query = self._get_search_query()
        if query:
            raw = filter_commands_fuzzy(raw, query, search_title=True, search_command=True)
        self._command_rows = raw
        self._selected_command_index = None
        for w in self._command_cards_frame.winfo_children():
            w.destroy()
        self._card_widgets.clear()
        self._command_cards_frame.configure(bg=self.theme["bg"])
        for idx, row in enumerate(self._command_rows):
            card = self._make_command_card(idx, row)
            self._card_widgets.append(card)

    def _make_command_card(self, idx: int, row: dict) -> dict:
        """One command card: single row — title | command | Copy Edit Delete. Double-click to copy."""
        theme = self.theme
        wrapper = tk.Frame(self._command_cards_frame, bg=theme["card_shadow"], padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=1)
        inner = tk.Frame(wrapper, bg=theme["card_bg"], padx=PAD_SM, pady=PAD_SM)
        inner.pack(fill=tk.X)
        inner.configure(highlightbackground=theme["card_border"], highlightthickness=1)

        title_lbl = tk.Label(inner, text=row["title"], font=theme["font_title"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        title_lbl.pack(side=tk.LEFT, padx=(0, PAD))
        cmd_preview = (row.get("command") or "").strip()
        cmd_preview = _truncate(cmd_preview, max_len=60) if cmd_preview else ""
        cmd_lbl = tk.Label(inner, text=cmd_preview or "(No command)", font=theme["font_command"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        cmd_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PAD))
        btn_frame = tk.Frame(inner, bg=theme["card_bg"])
        btn_frame.pack(side=tk.RIGHT)

        def copy_cb(i=idx):
            self._copy_by_index(i)
        def edit_cb(i=idx):
            self._edit_by_index(i)
        def delete_cb(i=idx):
            self._delete_by_index(i)

        copy_btn = ttk.Button(btn_frame, text="📋 Copy", command=copy_cb)
        copy_btn.pack(side=tk.LEFT, padx=(0, 2))
        edit_btn = ttk.Button(btn_frame, text="✏ Edit", command=edit_cb)
        edit_btn.pack(side=tk.LEFT, padx=(0, 2))
        del_btn = ttk.Button(btn_frame, text="🗑 Delete", command=delete_cb)
        del_btn.pack(side=tk.LEFT)

        def select_card(evt=None, i=idx):
            self._selected_command_index = i
            self._highlight_selected_card()

        def double_click_copy(evt=None, i=idx):
            self._selected_command_index = i
            self._highlight_selected_card()
            self._copy_by_index(i)

        def right_click(evt, i=idx):
            self._selected_command_index = i
            self._highlight_selected_card()
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="📋 Copy command", command=lambda: self._copy_by_index(i))
            menu.add_command(label="✏ Edit", command=lambda: self._edit_by_index(i))
            menu.add_command(label="🗑 Delete", command=lambda: self._delete_by_index(i))
            menu.tk_popup(evt.x_root, evt.y_root)

        for w in (wrapper, inner, title_lbl, cmd_lbl, btn_frame):
            w.bind("<Button-1>", select_card)
            w.bind("<Double-1>", double_click_copy)
            w.bind("<Button-3>", right_click)
        return {"wrapper": wrapper, "inner": inner, "idx": idx}

    def _highlight_selected_card(self) -> None:
        for card in self._card_widgets:
            inner = card["inner"]
            if card["idx"] == self._selected_command_index:
                inner.configure(highlightbackground=self.theme["accent_bg"], highlightthickness=2)
            else:
                inner.configure(highlightbackground=self.theme["card_border"], highlightthickness=1)

    def _copy_by_index(self, idx: int) -> Optional[str]:
        if idx < 0 or idx >= len(self._command_rows):
            return None
        row = self._command_rows[idx]
        cmd_text = (row.get("command") or "").strip() or (row.get("title") or "")
        copy_to_clipboard(self.root, cmd_text)
        self.status_var.set("Command copied to clipboard ✔")
        self._status_is_success = True
        self._update_status_style()
        self.root.after(2500, self._status_clear_success)
        return cmd_text

    def _status_clear_success(self) -> None:
        self._status_is_success = False
        self._update_status_style()
        if "✔" in self.status_var.get():
            self.status_var.set("Ready")

    def _copy_selected(self) -> Optional[str]:
        if self._selected_command_index is not None:
            return self._copy_by_index(self._selected_command_index)
        if self._command_rows:
            self._selected_command_index = 0
            self._highlight_selected_card()
            return self._copy_by_index(0)
        return None

    def _edit_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._command_rows):
            messagebox.showinfo("Info", "Select a command to edit.", parent=self.root)
            return
        row = self._command_rows[idx]
        dlg = CommandDialog(self.root, "Edit Command", self._category_list,
                           initial_title=row["title"], initial_command=row["command"],
                           initial_category_id=row["category_id"])
        if dlg.result_tuple:
            title, command, category_id = dlg.result_tuple
            db_module.update_command(self.conn, row["id"], title, command, category_id)
            self.refresh_commands()
            self.status_var.set("Command updated.")

    def _delete_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._command_rows):
            messagebox.showinfo("Info", "Select a command to delete.", parent=self.root)
            return
        row = self._command_rows[idx]
        if messagebox.askyesno("Confirm", f'Delete command "{row["title"]}"?', parent=self.root):
            db_module.delete_command(self.conn, row["id"])
            self.refresh_commands()
            self.status_var.set("Command deleted.")

    def _add_command(self) -> None:
        if not self._category_list:
            messagebox.showinfo("Info", "Add a category first.", parent=self.root)
            return
        dlg = CommandDialog(self.root, "Add Command", self._category_list,
                            initial_title="", initial_command="", initial_category_id=self.selected_category_id)
        if dlg.result_tuple:
            title, command, category_id = dlg.result_tuple
            db_module.add_command(self.conn, title, command, category_id)
            self.refresh_commands()
            self.status_var.set("Command added.")

    def _edit_command(self) -> None:
        if self._selected_command_index is not None:
            self._edit_by_index(self._selected_command_index)
        else:
            messagebox.showinfo("Info", "Select a command to edit.", parent=self.root)

    def _delete_command(self) -> None:
        if self._selected_command_index is not None:
            self._delete_by_index(self._selected_command_index)
        else:
            messagebox.showinfo("Info", "Select a command to delete.", parent=self.root)

    def _add_category(self) -> None:
        dlg = CategoryDialog(self.root, "Add Category")
        if dlg.result_name:
            try:
                db_module.add_category(self.conn, dlg.result_name)
                self.refresh_categories()
                self.status_var.set("Category added.")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "A category with that name already exists.", parent=self.root)

    def _delete_category(self) -> None:
        sel_idx = None
        for i, c in enumerate(self._category_list):
            if c["id"] == self.selected_category_id:
                sel_idx = i
                break
        if sel_idx is None and self._category_list:
            sel_idx = 0
        if sel_idx is None:
            messagebox.showinfo("Info", "Select a category to delete.", parent=self.root)
            return
        cat = self._category_list[sel_idx]
        n = db_module.count_commands_in_category(self.conn, cat["id"])
        if n > 0:
            if not messagebox.askyesno("Confirm", f'Category "{cat["name"]}" has {n} command(s). Delete anyway?', parent=self.root):
                return
        db_module.delete_category(self.conn, cat["id"])
        self.selected_category_id = None
        self.refresh_categories()
        self.refresh_commands()
        self.status_var.set("Category deleted.")

    # --- Secrets tab ---

    def refresh_secrets(self) -> None:
        self._secret_rows = db_module.list_secrets(self.conn)
        if not self._secrets_frame:
            return
        for w in self._secrets_frame.winfo_children():
            w.destroy()
        self._secrets_frame.configure(bg=self.theme["bg"])
        if not self._secret_rows:
            empty_lbl = tk.Label(self._secrets_frame, text="No secrets yet. Click \"➕ Add Secret\" to add one.",
                                 font=self.theme["font_ui"], bg=self.theme["bg"], fg=self.theme["fg"])
            empty_lbl.pack(anchor="w", pady=PAD)
        for idx, row in enumerate(self._secret_rows):
            self._make_secret_card(idx, row)

    def _make_secret_card(self, idx: int, row: dict) -> None:
        """One secret row: title | 🔒**** (click to view) | description | Copy Edit Delete."""
        theme = self.theme
        wrapper = tk.Frame(self._secrets_frame, bg=theme["card_shadow"], padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=1)
        inner = tk.Frame(wrapper, bg=theme["card_bg"], padx=PAD_SM, pady=PAD_SM)
        inner.pack(fill=tk.X)
        inner.configure(highlightbackground=theme["card_border"], highlightthickness=1)

        title_lbl = tk.Label(inner, text=row["title"], font=theme["font_title"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        title_lbl.pack(side=tk.LEFT, padx=(0, PAD))
        secret_text = (row.get("secret") or "").strip()
        secret_lbl = tk.Label(inner, text="🔒 ****", font=theme["font_ui"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w", cursor="hand2")
        secret_lbl.pack(side=tk.LEFT, padx=(0, PAD))
        desc = (row.get("description") or "").strip()
        desc_preview = _truncate(desc, 40) if desc else "(No description)"
        desc_lbl = tk.Label(inner, text=desc_preview, font=theme["font_command"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        desc_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PAD))
        btn_frame = tk.Frame(inner, bg=theme["card_bg"])
        btn_frame.pack(side=tk.RIGHT)

        def copy_secret_cb(i=idx):
            self._copy_secret_by_index(i)
        def edit_secret_cb(i=idx):
            self._edit_secret_by_index(i)
        def delete_secret_cb(i=idx):
            self._delete_secret_by_index(i)

        ttk.Button(btn_frame, text="📋 Copy", command=copy_secret_cb).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(btn_frame, text="✏ Edit", command=edit_secret_cb).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(btn_frame, text="🗑 Delete", command=delete_secret_cb).pack(side=tk.LEFT)

        def toggle_secret(evt=None, txt=secret_text, lbl=secret_lbl):
            if lbl.cget("text") == "🔒 ****":
                lbl.configure(text=txt)
                inner.after(5000, lambda: lbl.configure(text="🔒 ****"))
            else:
                lbl.configure(text="🔒 ****")
        secret_lbl.bind("<Button-1>", toggle_secret)

        def right_click_secret(evt, i=idx):
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="📋 Copy secret", command=lambda: self._copy_secret_by_index(i))
            menu.add_command(label="✏ Edit", command=lambda: self._edit_secret_by_index(i))
            menu.add_command(label="🗑 Delete", command=lambda: self._delete_secret_by_index(i))
            menu.tk_popup(evt.x_root, evt.y_root)
        for w in (wrapper, inner, title_lbl, secret_lbl, desc_lbl, btn_frame):
            w.bind("<Button-3>", right_click_secret)

    def _add_secret(self) -> None:
        dlg = SecretDialog(self.root, "Add Secret", initial_title="", initial_secret="", initial_description="")
        if dlg.result_tuple:
            title, secret, description = dlg.result_tuple
            db_module.add_secret(self.conn, title, secret, description)
            self.refresh_secrets()
            self.status_var.set("Secret added.")

    def _edit_secret_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._secret_rows):
            return
        row = self._secret_rows[idx]
        dlg = SecretDialog(self.root, "Edit Secret", initial_title=row["title"],
                          initial_secret=row.get("secret") or "",
                          initial_description=(row.get("description") or "") or "")
        if dlg.result_tuple:
            title, secret, description = dlg.result_tuple
            db_module.update_secret(self.conn, row["id"], title, secret, description)
            self.refresh_secrets()
            self.status_var.set("Secret updated.")

    def _delete_secret_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._secret_rows):
            return
        row = self._secret_rows[idx]
        if messagebox.askyesno("Confirm", f'Delete secret "{row["title"]}"?', parent=self.root):
            db_module.delete_secret(self.conn, row["id"])
            self.refresh_secrets()
            self.status_var.set("Secret deleted.")

    def _copy_secret_by_index(self, idx: int) -> Optional[str]:
        if idx < 0 or idx >= len(self._secret_rows):
            return None
        row = self._secret_rows[idx]
        secret = (row.get("secret") or "").strip()
        if not secret:
            return None
        copy_to_clipboard(self.root, secret)
        self.status_var.set("Secret copied to clipboard ✔")
        self._status_is_success = True
        self._update_status_style()
        self.root.after(2500, self._status_clear_success)
        return secret
