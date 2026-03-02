# cmdvault/ui.py
"""
Modern UI for CmdVault: ttk-themed sidebar, card-based command list,
search bar with placeholder, status bar, double-click to copy.
"""

import json
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Optional
from . import db as db_module
from .themes import get_theme, PAD, PAD_SM, PAD_LG
from .utils import copy_to_clipboard, filter_commands_fuzzy

SEARCH_PLACEHOLDER = "Search all commands…"
CMD_PREVIEW_LEN = 80

# Tag colors for command tags (Production, Debug, etc.)
TAG_COLORS = ("#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899")


def _truncate(s: str, max_len: int = CMD_PREVIEW_LEN) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _show_toast(root: tk.Tk, message: str, theme: Optional[dict] = None) -> None:
    """Non-intrusive toast bottom-right, auto-dismiss. Pass theme for colors."""
    tw = tk.Toplevel(root)
    tw.overrideredirect(1)
    tw.attributes("-topmost", 1)
    t = theme or {}
    bg = t.get("status_success_bg", "#064e3b")
    fg = t.get("status_success_fg", "#10b981")
    border = t.get("border", "#27272a")
    tw.configure(bg=border)
    f = tk.Frame(tw, bg=bg, padx=PAD_LG, pady=PAD_SM)
    f.pack(fill=tk.BOTH, padx=1, pady=1)
    tk.Label(f, text=message, font=("Sans", 10), bg=bg, fg=fg).pack()
    tw.update_idletasks()
    x = root.winfo_x() + root.winfo_width() - tw.winfo_reqwidth() - 24
    y = root.winfo_y() + root.winfo_height() - tw.winfo_reqheight() - 56
    tw.geometry(f"+{max(root.winfo_x(), x)}+{max(root.winfo_y(), y)}")
    tw.after(2200, tw.destroy)


# --- Dialogs ---

class CommandDialog(simpledialog.Dialog):
    """Modal dialog to add or edit a command: Title + Command + Category + Tags."""

    def __init__(self, parent, title: str, categories: list, initial_title: str = "",
                 initial_command: str = "", initial_category_id: Optional[int] = None, initial_tags: str = ""):
        self.categories = categories
        self.initial_title = initial_title
        self.initial_command = initial_command
        self.initial_category_id = initial_category_id
        self.initial_tags = initial_tags or ""
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
        ttk.Label(master, text="Tags:").grid(row=3, column=0, sticky="w", padx=PAD, pady=PAD_SM)
        self.tags_var = tk.StringVar(value=self.initial_tags)
        ttk.Entry(master, textvariable=self.tags_var, width=42).grid(row=3, column=1, padx=PAD, pady=PAD_SM)
        return self.title_entry

    def apply(self):
        title = self.title_var.get().strip()
        command = self.cmd_text.get("1.0", "end-1c").strip()
        cat_name = (self.cat_var.get() or "").strip()
        if not cat_name and self.categories:
            cat_name = self.categories[0]["name"]
        tags = (self.tags_var.get() or "").strip()
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
        self.result_tuple = (title, command, category_id, tags)


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


class NoteDialog(simpledialog.Dialog):
    """Modal dialog to add or edit a note: Title + Content."""

    def __init__(self, parent, dialog_title: str, initial_title: str = "", initial_content: str = ""):
        self.initial_title = initial_title
        self.initial_content = initial_content or ""
        self.result_tuple: Optional[tuple] = None
        super().__init__(parent, dialog_title)

    def body(self, master):
        master.winfo_toplevel().lift()
        ttk.Label(master, text="Title:").grid(row=0, column=0, sticky="w", padx=PAD, pady=PAD_SM)
        self.title_var = tk.StringVar(value=self.initial_title)
        self.title_entry = ttk.Entry(master, textvariable=self.title_var, width=42)
        self.title_entry.grid(row=0, column=1, padx=PAD, pady=PAD_SM)
        ttk.Label(master, text="Content:").grid(row=1, column=0, sticky="nw", padx=PAD, pady=PAD_SM)
        self.content_text = tk.Text(master, width=42, height=8, relief=tk.FLAT, padx=4, pady=4)
        self.content_text.insert("1.0", self.initial_content)
        self.content_text.grid(row=1, column=1, padx=PAD, pady=PAD_SM)
        return self.title_entry

    def apply(self):
        title = self.title_var.get().strip()
        content = self.content_text.get("1.0", "end-1c").strip()
        if not title:
            messagebox.showwarning("Validation", "Title is required.", parent=self)
            return
        self.result_tuple = (title, content)


class TodoDialog(simpledialog.Dialog):
    """Modal dialog to add or edit a todo: Title only."""

    def __init__(self, parent, dialog_title: str, initial_title: str = ""):
        self.initial_title = initial_title
        self.result_title: Optional[str] = None
        super().__init__(parent, dialog_title)

    def body(self, master):
        master.winfo_toplevel().lift()
        ttk.Label(master, text="Task:").grid(row=0, column=0, sticky="w", padx=PAD, pady=PAD)
        self.title_var = tk.StringVar(value=self.initial_title)
        self.entry = ttk.Entry(master, textvariable=self.title_var, width=42)
        self.entry.grid(row=0, column=1, padx=PAD, pady=PAD)
        return self.entry

    def apply(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Validation", "Task title is required.", parent=self)
            return
        self.result_title = title


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
        self._bulk_selected_ids: set = set()
        self._command_cards_frame: Optional[tk.Frame] = None
        self._card_widgets: list = []
        self._secrets_frame: Optional[tk.Frame] = None
        self._secret_rows: list = []
        self._notes_frame: Optional[tk.Frame] = None
        self._note_rows: list = []
        self._todos_frame: Optional[tk.Frame] = None
        self._todo_rows: list = []
        self._todo_filter: str = "all"  # "all" | "pending" | "done"
        self._status_is_success = False
        self._search_debounce_id: Optional[str] = None
        self._search_debounce_ms = 100
        self._search_cache: Optional[list] = None

        root.title("CmdVault")
        root.minsize(640, 420)
        root.geometry("960x580")
        root.configure(bg=self.theme["bg"])

        self._configure_styles()
        self._build_menus()
        self._build_layout()
        self._apply_theme(self.theme)
        self._bind_shortcuts()
        self._bind_all_canvas_scroll()

        self.refresh_categories()
        self.refresh_commands()
        self.refresh_secrets()
        self.refresh_notes()
        self.refresh_todos()
        self._todo_segment_refresh()
        self._select_first_category_if_any()

    def _load_dark_mode(self) -> bool:
        val = db_module.get_setting(self.conn, "dark_mode")
        if val is None:
            return True  # Default: Developer Dark theme
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
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _toggle_dark_mode(self) -> None:
        self.dark_mode = self.dark_mode_var.get()
        self._save_dark_mode(self.dark_mode)
        self.theme = get_theme(self.dark_mode)
        self._apply_theme(self.theme)

    def _show_about(self) -> None:
        """Show About dialog with version and doc link."""
        messagebox.showinfo(
            "About CmdVault",
            "CmdVault 2.0\n\nStore, search, and copy terminal commands.\n"
            "Commands · Secrets · Notes · Todo\n\n"
            "Install & troubleshooting: docs/INSTALL.md\n"
            "Sample import: samples/import_sample.json",
            parent=self.root,
        )

    def _import_from_file(self) -> None:
        """Import commands and secrets from a JSON file. See samples/import_sample.json for format."""
        initialdir = None
        try:
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(pkg_dir)
            samples_dir = os.path.join(project_root, "samples")
            if os.path.isdir(samples_dir):
                initialdir = samples_dir
        except Exception:
            pass
        path = filedialog.askopenfilename(
            title="Import from JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=initialdir,
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
        self._search_cache = None
        self.refresh_categories()
        self.refresh_commands()
        self.refresh_secrets()
        self.status_var.set(f"Import done: {n_commands} command(s), {n_secrets} secret(s).")
        messagebox.showinfo("Import", f"Imported {n_commands} command(s) and {n_secrets} secret(s).", parent=self.root)

    def _build_layout(self) -> None:
        self._main_frame = tk.Frame(self.root, bg=self.theme["bg"], padx=PAD, pady=PAD)
        self._main_frame.pack(fill=tk.BOTH, expand=True)
        main = self._main_frame

        # Global header: title left, search right (accessible from any tab)
        self._header_frame = tk.Frame(main, bg=self.theme["bg"])
        self._header_frame.pack(fill=tk.X, pady=(0, PAD_SM))
        header = self._header_frame
        tk.Label(header, text="CmdVault", font=self.theme["font_title"], bg=self.theme["bg"], fg=self.theme["fg"]).pack(side=tk.LEFT)
        search_inner = tk.Frame(header, bg=self.theme["bg"])
        search_inner.pack(side=tk.RIGHT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search_change())
        recent = db_module.get_recent_searches(self.conn)
        self.search_entry = ttk.Combobox(search_inner, textvariable=self.search_var, values=recent, width=36)
        self.search_entry.pack(side=tk.RIGHT, ipady=4, ipadx=PAD_SM)
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)
        self.search_entry.bind("<<ComboboxSelected>>", lambda e: self._on_search_change())
        self.search_entry.bind("<Return>", lambda e: self._search_apply_and_save())
        self._search_placeholder = ttk.Label(search_inner, text=SEARCH_PLACEHOLDER, style="Placeholder.TLabel")
        self._search_placeholder.bind("<Button-1>", lambda e: self._search_placeholder_click())
        self._search_placeholder.place(in_=self.search_entry, relx=0.02, rely=0, relwidth=0.96, relheight=1)
        tk.Label(header, text="Search", font=self.theme["font_ui"], bg=self.theme["bg"], fg=self.theme["fg"]).pack(side=tk.RIGHT, padx=(0, PAD_SM))

        self._notebook = ttk.Notebook(main)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # --- Tab 1: Commands ---
        tab_commands = ttk.Frame(self._notebook, padding=0)
        self._notebook.add(tab_commands, text="Commands")
        cmd_main = ttk.Frame(tab_commands)
        cmd_main.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(cmd_main, width=self.SIDEBAR_WIDTH, bg=self.theme["sidebar_bg"])
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PAD_LG))
        sidebar.pack_propagate(False)
        cat_header = tk.Frame(sidebar, bg=self.theme["sidebar_bg"])
        cat_header.pack(fill=tk.X, padx=PAD, pady=(0, PAD_SM))
        tk.Label(cat_header, text="Categories", font=self.theme["font_ui"], bg=self.theme["sidebar_bg"], fg=self.theme["sidebar_fg"]).pack(side=tk.LEFT)
        ttk.Button(cat_header, text="+", command=self._add_category, style="Accent.TButton", width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(cat_header, text="Del", command=self._delete_category).pack(side=tk.RIGHT)
        cat_list_frame = tk.Frame(sidebar, bg=self.theme["sidebar_bg"])
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

        right = ttk.Frame(cmd_main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cmd_top = tk.Frame(right, bg=self.theme["bg"])
        cmd_top.pack(fill=tk.X, pady=(0, PAD_SM))
        self._bulk_frame = tk.Frame(cmd_top, bg=self.theme["bg"])
        self._bulk_frame.pack(side=tk.LEFT)
        self._bulk_delete_btn = ttk.Button(self._bulk_frame, text="Bulk Delete", command=self._bulk_delete_commands, state=tk.DISABLED)
        self._bulk_delete_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._bulk_export_btn = ttk.Button(self._bulk_frame, text="Bulk Export", command=self._bulk_export_commands, state=tk.DISABLED)
        self._bulk_export_btn.pack(side=tk.LEFT)
        ttk.Button(cmd_top, text="Add Command", command=self._add_command, style="Accent.TButton").pack(side=tk.RIGHT)
        cards_container = ttk.Frame(right)
        cards_container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(cards_container, highlightthickness=0, bg=self.theme["bg"])
        scrollbar = ttk.Scrollbar(cards_container)
        self._command_cards_frame = tk.Frame(canvas, bg=self.theme["bg"])
        self._command_cards_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._command_cards_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.config(command=canvas.yview)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._cards_canvas = canvas

        # --- Tab 2: Secrets ---
        tab_secrets = ttk.Frame(self._notebook, padding=PAD)
        self._notebook.add(tab_secrets, text="Secrets")
        sec_top = tk.Frame(tab_secrets, bg=self.theme["bg"])
        sec_top.pack(fill=tk.X, pady=(0, PAD))
        tk.Label(sec_top, text="Secrets", font=self.theme["font_title"], bg=self.theme["bg"], fg=self.theme["fg"]).pack(side=tk.LEFT)
        ttk.Button(sec_top, text="Add Secret", command=self._add_secret, style="Accent.TButton").pack(side=tk.RIGHT)
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

        # --- Tab 3: Notes ---
        tab_notes = ttk.Frame(self._notebook, padding=PAD)
        self._notebook.add(tab_notes, text="Notes")
        notes_top = tk.Frame(tab_notes, bg=self.theme["bg"])
        notes_top.pack(fill=tk.X, pady=(0, PAD))
        tk.Label(notes_top, text="Notes", font=self.theme["font_title"], bg=self.theme["bg"], fg=self.theme["fg"]).pack(side=tk.LEFT)
        ttk.Button(notes_top, text="Add Note", command=self._add_note, style="Accent.TButton").pack(side=tk.RIGHT)
        notes_scroll = ttk.Frame(tab_notes)
        notes_scroll.pack(fill=tk.BOTH, expand=True)
        n_canvas = tk.Canvas(notes_scroll, highlightthickness=0)
        n_scrollbar = ttk.Scrollbar(notes_scroll)
        self._notes_frame = tk.Frame(n_canvas)
        self._notes_frame.bind("<Configure>", lambda e: n_canvas.configure(scrollregion=n_canvas.bbox("all")))
        n_canvas.create_window((0, 0), window=self._notes_frame, anchor="nw")
        n_canvas.configure(yscrollcommand=n_scrollbar.set)
        n_scrollbar.config(command=n_canvas.yview)
        n_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        n_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._notes_canvas = n_canvas

        # --- Tab 4: Todo (segment control for filter) ---
        tab_todos = ttk.Frame(self._notebook, padding=PAD)
        self._notebook.add(tab_todos, text="Todo")
        todos_top = tk.Frame(tab_todos, bg=self.theme["bg"])
        todos_top.pack(fill=tk.X, pady=(0, PAD))
        tk.Label(todos_top, text="Daily tasks", font=self.theme["font_title"], bg=self.theme["bg"], fg=self.theme["fg"]).pack(side=tk.LEFT, padx=(0, PAD))
        ttk.Button(todos_top, text="Add task", command=self._add_todo, style="Accent.TButton").pack(side=tk.RIGHT, padx=(0, PAD))
        seg_frame = tk.Frame(todos_top, bg=self.theme["border"], padx=1, pady=1)
        seg_frame.pack(side=tk.LEFT, padx=PAD)
        self._todo_filter_var = tk.StringVar(value="all")
        self._todo_seg_buttons = []
        for val, lbl in (("all", "All"), ("pending", "Pending"), ("done", "Done")):
            b = tk.Label(seg_frame, text=lbl, font=self.theme["font_ui"], padx=12, pady=4, cursor="hand2")
            b.pack(side=tk.LEFT)
            b.bind("<Button-1>", lambda e, v=val: self._todo_filter_set(v))
            self._todo_seg_buttons.append((val, b))
        ttk.Button(todos_top, text="Clear completed", command=self._todo_clear_completed).pack(side=tk.LEFT, padx=PAD)
        todos_scroll = ttk.Frame(tab_todos)
        todos_scroll.pack(fill=tk.BOTH, expand=True)
        t_canvas = tk.Canvas(todos_scroll, highlightthickness=0)
        t_scrollbar = ttk.Scrollbar(todos_scroll)
        self._todos_frame = tk.Frame(t_canvas)
        self._todos_frame.bind("<Configure>", lambda e: t_canvas.configure(scrollregion=t_canvas.bbox("all")))
        t_canvas.create_window((0, 0), window=self._todos_frame, anchor="nw")
        t_canvas.configure(yscrollcommand=t_scrollbar.set)
        t_scrollbar.config(command=t_canvas.yview)
        t_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        t_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._todos_canvas = t_canvas

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
        if self._search_debounce_id:
            self.root.after_cancel(self._search_debounce_id)
        self._search_debounce_id = self.root.after(self._search_debounce_ms, self._search_debounced_refresh)

    def _search_debounced_refresh(self) -> None:
        self._search_debounce_id = None
        self.refresh_commands()
        q = self.search_var.get().strip()
        if q:
            db_module.add_recent_search(self.conn, q)
            self.search_entry["values"] = db_module.get_recent_searches(self.conn)

    def _search_apply_and_save(self) -> None:
        q = self.search_var.get().strip()
        if q:
            db_module.add_recent_search(self.conn, q)
            recent = db_module.get_recent_searches(self.conn)
            self.search_entry["values"] = recent
        self.refresh_commands()

    def _get_search_query(self) -> str:
        return self.search_var.get().strip()

    def _bind_canvas_scroll(self, canvas, inner_frame=None) -> None:
        """Bind mousewheel and Linux Button-4/5 so two-finger scroll works."""

        def do_scroll(evt, canvas=canvas):
            # Linux: Button-4 = up, Button-5 = down. Windows/Mac: delta
            delta = 0
            if hasattr(evt, "num"):
                if evt.num == 4:
                    delta = -1
                elif evt.num == 5:
                    delta = 1
            elif hasattr(evt, "delta"):
                delta = -1 if evt.delta > 0 else 1
            if delta != 0:
                canvas.yview_scroll(3 * delta, "units")

        canvas.bind("<MouseWheel>", do_scroll)
        canvas.bind("<Button-4>", do_scroll)
        canvas.bind("<Button-5>", do_scroll)
        if inner_frame is not None:
            inner_frame.bind("<MouseWheel>", do_scroll)
            inner_frame.bind("<Button-4>", do_scroll)
            inner_frame.bind("<Button-5>", do_scroll)

    def _bind_all_canvas_scroll(self) -> None:
        """Attach two-finger/mousewheel scroll to all scrollable canvases."""
        self._bind_canvas_scroll(self._cat_canvas, self.cat_inner)
        self._bind_canvas_scroll(self._cards_canvas, self._command_cards_frame)
        self._bind_canvas_scroll(self._secrets_canvas, self._secrets_frame)
        self._bind_canvas_scroll(self._notes_canvas, self._notes_frame)
        self._bind_canvas_scroll(self._todos_canvas, self._todos_frame)

    def _apply_theme(self, theme: dict) -> None:
        self.theme = theme
        self.root.configure(bg=theme["bg"])
        if hasattr(self, "_main_frame"):
            self._main_frame.configure(bg=theme["bg"])
        if hasattr(self, "_header_frame"):
            self._header_frame.configure(bg=theme["bg"])
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
        if hasattr(self, "_notes_canvas"):
            self._notes_canvas.configure(bg=theme["bg"])
        if hasattr(self, "_notes_frame"):
            self._notes_frame.configure(bg=theme["bg"])
        if hasattr(self, "_todos_canvas"):
            self._todos_canvas.configure(bg=theme["bg"])
        if hasattr(self, "_todos_frame"):
            self._todos_frame.configure(bg=theme["bg"])
        for i, (f, accent, lbl) in enumerate(self._category_frames):
            is_selected = (self.selected_category_id is not None and i < len(self._category_list) and
                          self._category_list[i]["id"] == self.selected_category_id)
            f.configure(bg=theme["sidebar_select_bg"] if is_selected else theme["sidebar_bg"])
            accent.configure(bg=theme["sidebar_accent"] if is_selected else theme["sidebar_bg"])
            lbl.configure(bg=f["bg"], fg=theme["sidebar_fg"])
        self._update_status_style()
        self.refresh_commands()
        self.refresh_secrets()
        self.refresh_notes()
        self.refresh_todos()
        self._todo_segment_refresh()

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
            n = db_module.count_commands_in_category(self.conn, c["id"])
            display_name = f"{c['name']} ({n})"
            row = tk.Frame(self.cat_inner, bg=self.theme["sidebar_select_bg"] if is_selected else self.theme["sidebar_bg"], cursor="hand2")
            accent = tk.Frame(row, width=4, bg=self.theme["sidebar_accent"] if is_selected else self.theme["sidebar_bg"])
            accent.pack(side=tk.LEFT, fill=tk.Y)
            lbl = tk.Label(row, text=display_name, font=self.theme["font_ui"], bg=row["bg"], fg=self.theme["sidebar_fg"], anchor="w", padx=PAD, pady=PAD_SM)
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

    # Max command cards to render so search stays fast
    _COMMAND_DISPLAY_LIMIT = 120

    def refresh_commands(self) -> None:
        query = self._get_search_query()
        if query:
            if self._search_cache is None:
                self._search_cache = db_module.list_commands(self.conn, category_id=None)
            raw = filter_commands_fuzzy(self._search_cache, query, search_title=True, search_command=True)
        else:
            self._search_cache = None
            raw = db_module.list_commands(self.conn, category_id=self.selected_category_id)
        total = len(raw)
        display = raw[: self._COMMAND_DISPLAY_LIMIT]
        self._command_rows = display
        self._selected_command_index = None
        for w in self._command_cards_frame.winfo_children():
            w.destroy()
        self._card_widgets.clear()
        self._command_cards_frame.configure(bg=self.theme["bg"])
        for idx, row in enumerate(self._command_rows):
            card = self._make_command_card(idx, row)
            self._card_widgets.append(card)
        if total > self._COMMAND_DISPLAY_LIMIT:
            cap_lbl = tk.Label(
                self._command_cards_frame,
                text=f"Showing first {self._COMMAND_DISPLAY_LIMIT} of {total} matches. Refine search to see fewer.",
                font=self.theme["font_ui"],
                bg=self.theme["bg"],
                fg=self.theme["entry_placeholder_fg"],
            )
            cap_lbl.pack(fill=tk.X, pady=PAD_SM)
        self._bulk_buttons_update()

    def _make_command_card(self, idx: int, row: dict) -> dict:
        """Card: title + tags chips + command preview; ghost Copy/Edit/Delete on hover."""
        theme = self.theme
        border = theme.get("border", theme["card_border"])
        wrapper = tk.Frame(self._command_cards_frame, bg=border, padx=1, pady=2)
        wrapper.pack(fill=tk.X, pady=2)
        inner = tk.Frame(wrapper, bg=theme["card_bg"], padx=PAD_SM, pady=PAD_SM)
        inner.pack(fill=tk.X)
        inner.configure(highlightbackground=border, highlightthickness=1)

        # Row 1: bulk checkbox + title (+ category when search) + command preview
        row1 = tk.Frame(inner, bg=theme["card_bg"])
        row1.pack(fill=tk.X)
        cmd_id = row.get("id")
        bulk_var = tk.BooleanVar(value=cmd_id in self._bulk_selected_ids)
        def on_bulk_toggle(i=cmd_id, v=bulk_var):
            if v.get():
                self._bulk_selected_ids.add(i)
            else:
                self._bulk_selected_ids.discard(i)
            self._bulk_buttons_update()
        cb = tk.Checkbutton(row1, variable=bulk_var, command=on_bulk_toggle, bg=theme["card_bg"], fg=theme["card_fg"], activebackground=theme["card_bg"], selectcolor=theme["card_bg"])
        cb.pack(side=tk.LEFT, padx=(0, PAD_SM))
        title_text = row["title"]
        if self._get_search_query() and self._category_list:
            cat_id = row.get("category_id")
            cat_name = next((c["name"] for c in self._category_list if c["id"] == cat_id), None)
            if cat_name:
                title_text = f"[{cat_name}] {title_text}"
        title_lbl = tk.Label(row1, text=title_text, font=theme["font_title"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        title_lbl.pack(side=tk.LEFT, padx=(0, PAD))
        cmd_preview = (row.get("command") or "").strip()
        cmd_preview = _truncate(cmd_preview, max_len=60) if cmd_preview else ""
        cmd_lbl = tk.Label(row1, text=cmd_preview or "(No command)", font=theme["font_command"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        cmd_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PAD))

        # Tags as colored chips
        tags_str = (row.get("tags") or "").strip()
        if tags_str:
            tag_frame = tk.Frame(inner, bg=theme["card_bg"])
            tag_frame.pack(fill=tk.X, pady=(2, 0))
            for i, tag in enumerate([t.strip() for t in tags_str.split(",") if t.strip()][:5]):
                color = TAG_COLORS[hash(tag) % len(TAG_COLORS)]
                tk.Label(tag_frame, text=tag, font=("Sans", 8), bg=color, fg="#fff", padx=6, pady=1).pack(side=tk.LEFT, padx=(0, 4))

        # Ghost action buttons: show only on hover
        btn_frame = tk.Frame(inner, bg=theme["card_bg"])
        def copy_cb(i=idx):
            self._copy_by_index(i)
        def edit_cb(i=idx):
            self._edit_by_index(i)
        def delete_cb(i=idx):
            self._delete_by_index(i)
        copy_btn = tk.Button(btn_frame, text="\u2398", font=("Sans", 10), relief=tk.FLAT, bg=theme["card_bg"], fg=theme["button_fg"], activebackground=theme["button_hover_bg"], activeforeground=theme["fg"], cursor="hand2", command=copy_cb)
        copy_btn.pack(side=tk.LEFT, padx=(0, 2))
        edit_btn = tk.Button(btn_frame, text="\u270E", font=("Sans", 10), relief=tk.FLAT, bg=theme["card_bg"], fg=theme["button_fg"], activebackground=theme["button_hover_bg"], activeforeground=theme["fg"], cursor="hand2", command=edit_cb)
        edit_btn.pack(side=tk.LEFT, padx=(0, 2))
        del_btn = tk.Button(btn_frame, text="\u2716", font=("Sans", 10), relief=tk.FLAT, bg=theme["card_bg"], fg=theme["danger"], activebackground=theme["button_hover_bg"], activeforeground=theme["danger"], cursor="hand2", command=delete_cb)
        del_btn.pack(side=tk.LEFT)

        def show_btns(e):
            btn_frame.pack(fill=tk.X, pady=(PAD_SM, 0))
        def hide_btns(e):
            btn_frame.pack_forget()
        wrapper.bind("<Enter>", show_btns)
        wrapper.bind("<Leave>", hide_btns)
        inner.bind("<Enter>", show_btns)
        inner.bind("<Leave>", hide_btns)
        for w in (row1, title_lbl, cmd_lbl, copy_btn, edit_btn, del_btn, cb):
            if hasattr(w, "bind"):
                w.bind("<Enter>", show_btns)
                w.bind("<Leave>", hide_btns)

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
            menu.add_command(label="Copy", command=lambda: self._copy_by_index(i))
            menu.add_command(label="Edit", command=lambda: self._edit_by_index(i))
            menu.add_command(label="Delete", command=lambda: self._delete_by_index(i))
            menu.tk_popup(evt.x_root, evt.y_root)

        for w in (wrapper, inner, row1, title_lbl, cmd_lbl):
            w.bind("<Button-1>", select_card)
            w.bind("<Double-1>", double_click_copy)
            w.bind("<Button-3>", right_click)
        for b in (copy_btn, edit_btn, del_btn):
            b.bind("<Button-3>", right_click)
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
        _show_toast(self.root, "Copied to clipboard", self.theme)
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
                           initial_category_id=row["category_id"], initial_tags=(row.get("tags") or ""))
        if dlg.result_tuple:
            title, command, category_id, tags = dlg.result_tuple
            db_module.update_command(self.conn, row["id"], title, command, category_id, tags=tags)
            self._search_cache = None
            self.refresh_commands()
            self.status_var.set("Command updated.")

    def _delete_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._command_rows):
            messagebox.showinfo("Info", "Select a command to delete.", parent=self.root)
            return
        row = self._command_rows[idx]
        if messagebox.askyesno("Confirm", f'Delete command "{row["title"]}"?', parent=self.root):
            db_module.delete_command(self.conn, row["id"])
            self._search_cache = None
            self.refresh_commands()
            self.status_var.set("Command deleted.")

    def _bulk_buttons_update(self) -> None:
        if not hasattr(self, "_bulk_delete_btn"):
            return
        n = len(self._bulk_selected_ids)
        state = tk.NORMAL if n > 0 else tk.DISABLED
        self._bulk_delete_btn.configure(state=state)
        self._bulk_export_btn.configure(state=state)

    def _bulk_delete_commands(self) -> None:
        if not self._bulk_selected_ids:
            return
        if not messagebox.askyesno("Confirm", f"Delete {len(self._bulk_selected_ids)} selected command(s)?", parent=self.root):
            return
        for cid in list(self._bulk_selected_ids):
            db_module.delete_command(self.conn, cid)
        self._bulk_selected_ids.clear()
        self._search_cache = None
        self.refresh_commands()
        self.refresh_categories()
        self.status_var.set("Bulk delete done.")

    def _bulk_export_commands(self) -> None:
        if not self._bulk_selected_ids:
            return
        path = filedialog.asksaveasfilename(title="Export selected", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        rows = [r for r in self._command_rows if r.get("id") in self._bulk_selected_ids]
        cat_ids = {r["category_id"] for r in rows}
        cat_id_to_name = {c["id"]: c["name"] for c in self._category_list}
        export = {"commands": [{"title": r["title"], "command": r["command"], "category": cat_id_to_name.get(r["category_id"], ""), "tags": (r.get("tags") or "").strip()} for r in rows]}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=2)
            self.status_var.set(f"Exported {len(rows)} command(s).")
        except OSError as e:
            messagebox.showerror("Export failed", str(e), parent=self.root)

    def _add_command(self) -> None:
        if not self._category_list:
            messagebox.showinfo("Info", "Add a category first.", parent=self.root)
            return
        dlg = CommandDialog(self.root, "Add Command", self._category_list,
                            initial_title="", initial_command="", initial_category_id=self.selected_category_id, initial_tags="")
        if dlg.result_tuple:
            title, command, category_id, tags = dlg.result_tuple
            db_module.add_command(self.conn, title, command, category_id, tags=tags)
            self._search_cache = None
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
        self._search_cache = None
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
        """Two-row secret card: row1 = title, 🔒****, description; row2 = Copy | Edit | Delete."""
        theme = self.theme
        wrapper = tk.Frame(self._secrets_frame, bg=theme["card_shadow"], padx=1, pady=2)
        wrapper.pack(fill=tk.X, pady=2)
        inner = tk.Frame(wrapper, bg=theme["card_bg"], padx=PAD_SM, pady=PAD_SM)
        inner.pack(fill=tk.X)
        inner.configure(highlightbackground=theme["card_border"], highlightthickness=1)

        row1 = tk.Frame(inner, bg=theme["card_bg"])
        row1.pack(fill=tk.X)
        title_lbl = tk.Label(row1, text=row["title"], font=theme["font_title"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        title_lbl.pack(side=tk.LEFT, padx=(0, PAD))
        secret_text = (row.get("secret") or "").strip()
        secret_lbl = tk.Label(row1, text="****", font=theme["font_mono"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w", cursor="hand2")
        secret_lbl.pack(side=tk.LEFT, padx=(0, PAD_SM))
        def toggle_visibility(evt=None, txt=secret_text, lbl=secret_lbl):
            if lbl.cget("text") == "****":
                lbl.configure(text=txt)
                inner.after(5000, lambda: lbl.configure(text="****"))
            else:
                lbl.configure(text="****")
        eye_btn = tk.Label(row1, text="Show", font=("Sans", 9), bg=theme["card_bg"], fg=theme["accent_bg"], cursor="hand2")
        eye_btn.pack(side=tk.LEFT, padx=(0, PAD_SM))
        eye_btn.bind("<Button-1>", toggle_visibility)
        secret_lbl.bind("<Button-1>", toggle_visibility)
        desc = (row.get("description") or "").strip()
        desc_preview = _truncate(desc, 40) if desc else "(No description)"
        desc_lbl = tk.Label(row1, text=desc_preview, font=theme["font_command"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        desc_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PAD))
        btn_frame = tk.Frame(inner, bg=theme["card_bg"])
        btn_frame.pack(fill=tk.X, pady=(PAD_SM, 0))

        def copy_secret_cb(i=idx):
            self._copy_secret_by_index(i)
        def edit_secret_cb(i=idx):
            self._edit_secret_by_index(i)
        def delete_secret_cb(i=idx):
            self._delete_secret_by_index(i)

        ttk.Button(btn_frame, text="Copy", command=copy_secret_cb).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Edit", command=edit_secret_cb).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Delete", command=delete_secret_cb).pack(side=tk.LEFT)


        def right_click_secret(evt, i=idx):
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Copy secret", command=lambda: self._copy_secret_by_index(i))
            menu.add_command(label="Edit", command=lambda: self._edit_secret_by_index(i))
            menu.add_command(label="Delete", command=lambda: self._delete_secret_by_index(i))
            menu.tk_popup(evt.x_root, evt.y_root)
        for w in (wrapper, inner, row1, title_lbl, secret_lbl, eye_btn, desc_lbl, btn_frame):
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
        _show_toast(self.root, "Copied to clipboard", self.theme)
        return secret

    # --- Notes tab (two-column grid for wide screens) ---

    NOTES_COLUMNS = 2

    def refresh_notes(self) -> None:
        self._note_rows = db_module.list_notes(self.conn)
        if not self._notes_frame:
            return
        for w in self._notes_frame.winfo_children():
            w.destroy()
        self._notes_frame.configure(bg=self.theme["bg"])
        for c in range(self.NOTES_COLUMNS):
            self._notes_frame.columnconfigure(c, weight=1, uniform="notes")
        if not self._note_rows:
            lbl = tk.Label(self._notes_frame, text="No notes yet. Click \"Add Note\" to add one.",
                           font=self.theme["font_ui"], bg=self.theme["bg"], fg=self.theme["fg"])
            lbl.grid(row=0, column=0, columnspan=self.NOTES_COLUMNS, sticky="w", pady=PAD)
        else:
            for idx, row in enumerate(self._note_rows):
                r, c = divmod(idx, self.NOTES_COLUMNS)
                self._make_note_card(idx, row, r, c)

    def _make_note_card(self, idx: int, row: dict, grid_row: int, grid_col: int) -> None:
        theme = self.theme
        cell = tk.Frame(self._notes_frame, bg=theme["card_bg"], padx=PAD_SM, pady=PAD_SM, highlightbackground=theme["card_border"], highlightthickness=1)
        cell.grid(row=grid_row, column=grid_col, sticky="nsew", padx=2, pady=2)
        title_lbl = tk.Label(cell, text=row["title"], font=theme["font_title"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w")
        title_lbl.pack(fill=tk.X, padx=(0, PAD))
        content = (row.get("content") or "").strip()
        content_preview = _truncate(content, 80) if content else "(No content)"
        content_lbl = tk.Label(cell, text=content_preview, font=theme["font_command"], bg=theme["card_bg"], fg=theme["card_fg"], anchor="w", justify=tk.LEFT, wraplength=220)
        content_lbl.pack(fill=tk.X, padx=(0, PAD))
        btn_frame = tk.Frame(cell, bg=theme["card_bg"])
        btn_frame.pack(fill=tk.X, pady=(PAD_SM, 0))
        ttk.Button(btn_frame, text="Copy", command=lambda i=idx: self._copy_note_content_by_index(i)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Edit", command=lambda i=idx: self._edit_note_by_index(i)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Delete", command=lambda i=idx: self._delete_note_by_index(i)).pack(side=tk.LEFT)
        for w in (cell, title_lbl, content_lbl, btn_frame):
            w.bind("<Button-3>", lambda e, i=idx: self._note_right_click(e, i))

    def _note_right_click(self, evt, idx: int) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Copy content only", command=lambda: self._copy_note_content_by_index(idx))
        menu.add_command(label="Copy with title", command=lambda: self._copy_note_with_title_by_index(idx))
        menu.add_separator()
        menu.add_command(label="Edit", command=lambda: self._edit_note_by_index(idx))
        menu.add_command(label="Delete", command=lambda: self._delete_note_by_index(idx))
        menu.tk_popup(evt.x_root, evt.y_root)

    def _copy_note_content_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._note_rows):
            return
        row = self._note_rows[idx]
        content = (row.get("content") or "").strip()
        copy_to_clipboard(self.root, content)
        _show_toast(self.root, "Copied to clipboard", self.theme)

    def _copy_note_with_title_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._note_rows):
            return
        row = self._note_rows[idx]
        title = (row.get("title") or "").strip()
        content = (row.get("content") or "").strip()
        text = f"{title}\n\n{content}" if title else content
        copy_to_clipboard(self.root, text)
        _show_toast(self.root, "Copied to clipboard", self.theme)

    def _add_note(self) -> None:
        dlg = NoteDialog(self.root, "Add Note", initial_title="", initial_content="")
        if dlg.result_tuple:
            title, content = dlg.result_tuple
            db_module.add_note(self.conn, title, content)
            self.refresh_notes()
            self.status_var.set("Note added.")

    def _edit_note_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._note_rows):
            return
        row = self._note_rows[idx]
        dlg = NoteDialog(self.root, "Edit Note", initial_title=row["title"], initial_content=row.get("content") or "")
        if dlg.result_tuple:
            title, content = dlg.result_tuple
            db_module.update_note(self.conn, row["id"], title, content)
            self.refresh_notes()
            self.status_var.set("Note updated.")

    def _delete_note_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._note_rows):
            return
        row = self._note_rows[idx]
        if messagebox.askyesno("Confirm", f'Delete note "{row["title"]}"?', parent=self.root):
            db_module.delete_note(self.conn, row["id"])
            self.refresh_notes()
            self.status_var.set("Note deleted.")

    # --- Todo tab (vertical list + filter + clear completed) ---

    def _todo_filter_changed(self) -> None:
        self._todo_filter = self._todo_filter_var.get() or "all"
        self._todo_segment_refresh()
        self.refresh_todos()

    def _todo_filter_set(self, val: str) -> None:
        self._todo_filter_var.set(val)
        self._todo_filter_changed()

    def _todo_segment_refresh(self) -> None:
        current = self._todo_filter_var.get() or "all"
        for val, b in getattr(self, "_todo_seg_buttons", []):
            if val == current:
                b.configure(bg=self.theme["accent_bg"], fg=self.theme["accent_fg"])
            else:
                b.configure(bg=self.theme["card_bg"], fg=self.theme["button_fg"])

    def _todo_clear_completed(self) -> None:
        n = db_module.delete_completed_todos(self.conn)
        self.refresh_todos()
        self.status_var.set(f"Cleared {n} completed task(s)." if n else "No completed tasks to clear.")

    def refresh_todos(self) -> None:
        self._todo_rows = db_module.list_todos(self.conn)
        self._todo_filter = self._todo_filter_var.get() if hasattr(self, "_todo_filter_var") else "all"
        if self._todo_filter == "pending":
            self._todo_rows = [r for r in self._todo_rows if r.get("done", 0) != 1]
        elif self._todo_filter == "done":
            self._todo_rows = [r for r in self._todo_rows if r.get("done", 0) == 1]
        if not self._todos_frame:
            return
        for w in self._todos_frame.winfo_children():
            w.destroy()
        self._todos_frame.configure(bg=self.theme["bg"])
        if not self._todo_rows:
            msg = "No tasks yet." if self._todo_filter == "all" else f"No {self._todo_filter} tasks."
            lbl = tk.Label(self._todos_frame, text=msg + ' Click "Add task" to add one.' if self._todo_filter == "all" else msg,
                           font=self.theme["font_ui"], bg=self.theme["bg"], fg=self.theme["fg"])
            lbl.pack(anchor="w", pady=PAD)
        else:
            for idx, row in enumerate(self._todo_rows):
                self._make_todo_row(idx, row)

    def _make_todo_row(self, idx: int, row: dict) -> None:
        theme = self.theme
        done = row.get("done", 0) == 1
        wrapper = tk.Frame(self._todos_frame, bg=theme["card_shadow"], padx=1, pady=2, cursor="hand2")
        wrapper.pack(fill=tk.X, pady=2)
        inner = tk.Frame(wrapper, bg=theme["card_bg"], padx=PAD_SM, pady=PAD_SM, cursor="hand2")
        inner.pack(fill=tk.X)
        inner.configure(highlightbackground=theme["card_border"], highlightthickness=1)
        row_f = tk.Frame(inner, bg=theme["card_bg"], cursor="hand2")
        row_f.pack(fill=tk.X)
        title_font = theme["font_ui"]
        if done:
            try:
                import tkinter.font as tkfont
                t = title_font if isinstance(title_font, (list, tuple)) else (title_font,)
                f = tkfont.Font(family=t[0] if t else "Sans", size=t[1] if len(t) > 1 else 10, weight=t[2] if len(t) > 2 else "normal")
                f.configure(overstrike=True)
                title_font = f
            except Exception:
                pass
        title_lbl = tk.Label(row_f, text=row["title"], font=title_font, bg=theme["card_bg"], fg=theme["entry_placeholder_fg"] if done else theme["card_fg"], anchor="w", cursor="hand2")
        title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PAD))
        def on_double_click(e, i=idx):
            self._toggle_todo_done(i)
        for w in (wrapper, inner, row_f, title_lbl):
            w.bind("<Double-1>", on_double_click)
            w.bind("<Button-3>", lambda e, i=idx: self._todo_right_click(e, i))

    def _todo_right_click(self, evt, idx: int) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Toggle done", command=lambda: self._toggle_todo_done(idx))
        menu.tk_popup(evt.x_root, evt.y_root)

    def _add_todo(self) -> None:
        dlg = TodoDialog(self.root, "Add task", initial_title="")
        if dlg.result_title:
            db_module.add_todo(self.conn, dlg.result_title)
            self.refresh_todos()
            self.status_var.set("Task added.")

    def _toggle_todo_done(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._todo_rows):
            return
        row = self._todo_rows[idx]
        db_module.toggle_todo_done(self.conn, row["id"])
        self.refresh_todos()
        self.status_var.set("Task updated.")
