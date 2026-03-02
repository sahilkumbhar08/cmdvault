# CmdVault

**A desktop app to store, search, and copy terminal commands.** Developer-focused: dark theme, Notes, Todo, command tags, and fast search. Organize commands by category, use global search with recent history, and paste into your terminal with one click or double-click.

- **Platform:** Linux (tested on Fedora)
- **Stack:** Python 3.9+, Tkinter, SQLite — no extra dependencies for running
- **Data:** `~/.local/share/cmdvault/cmdvault.db` ([XDG](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html))

---

## Table of contents

- [Requirements](#requirements)
- [Quick start (run from source)](#quick-start-run-from-source)
- [Installation](#installation)
- [Project structure](#project-structure)
- [Import / export](#import--export)
- [Features](#features)
- [Contributing](#contributing)
- [License](#license)

---

## Requirements

- **Python 3.9+** with **tkinter** (usually bundled; on Fedora: `python3`, `python3-tkinter`)
- No `pip` install needed to run the app

---

## Quick start (run from source)

```bash
git clone https://github.com/sahilkumbhar08/cmdvault.git
cd cmdvault
python3 -m cmdvault.main
```

Or with the run script:

```bash
python3 run_cmdvault.py
```

---

## Installation

Choose one way to run CmdVault as a normal app.

| Method | Use case |
|--------|----------|
| [Home install (recommended)](#option-a-install-to-home-no-sudo) | App menu + `cmdvault` in terminal, no `sudo` |
| [RPM](#option-b-rpm-system-wide) | System-wide install on Fedora |
| [Standalone binary](#option-c-standalone-executable) | Single file, no Python required |

### Option A — Install to home (no sudo)

Installs to `~/.local` and adds CmdVault to your app menu.

```bash
git clone https://github.com/sahilkumbhar08/cmdvault.git
cd cmdvault
chmod +x install.sh
./install.sh
```

Then:

- **App menu:** Open your app launcher and search for **CmdVault** (under Utility / Development).
- **Terminal:** Run `~/.local/bin/cmdvault`. To use the short name `cmdvault`, add to `~/.bashrc`:
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  ```

See [docs/INSTALL.md](docs/INSTALL.md) for more detail and troubleshooting.

### Option B — RPM (system-wide)

For Fedora, build and install an RPM (use version 2.0 for current release):

```bash
cp -r cmdvault cmdvault-2.0
tar czvf cmdvault-2.0.tar.gz --exclude=__pycache__ --exclude=*.pyc cmdvault-2.0
sudo dnf install rpm-build
rpmbuild -ta cmdvault-2.0.tar.gz
sudo dnf install ~/rpmbuild/RPMS/noarch/cmdvault-2.0-1.fc*.noarch.rpm
```

Then run **CmdVault** from the app menu or the `cmdvault` command.

### Option C — Standalone executable

Build a single binary (no Python needed on the target machine):

```bash
pip install pyinstaller
chmod +x build_app.sh
./build_app.sh
./dist/CmdVault
```

Copy `dist/CmdVault` to e.g. `~/bin` to run it from anywhere. Data is still in `~/.local/share/cmdvault/`.

---

## Project structure

```
cmdvault/
├── cmdvault/              # Main package
│   ├── __init__.py
│   ├── __main__.py        # Entry for python3 -m cmdvault & PyInstaller
│   ├── main.py            # App entry, Tk window
│   ├── ui.py              # UI (tabs, sidebar, cards, search, dialogs)
│   ├── db.py              # SQLite (categories, commands, secrets, notes, todos, settings)
│   ├── themes.py          # Developer dark (Slate/Zinc) + light theme
│   └── utils.py           # Clipboard, fast search filter
├── docs/
│   └── INSTALL.md         # Detailed install and troubleshooting
├── samples/
│   └── import_sample.json # Example for File → Import (DevStack/OpenStack commands)
├── tests/
│   ├── __init__.py
│   └── test_db.py         # Basic DB tests (no GUI)
├── packaging/
│   └── cmdvault.desktop   # Desktop entry for app menu
├── run_cmdvault.py        # Convenience launcher
├── install.sh             # Install to ~/.local
├── build_app.sh           # Build standalone binary (PyInstaller)
├── cmdvault.spec          # RPM spec (Fedora), version 2.0
├── cmdvault_app.spec      # PyInstaller spec
├── requirements.txt       # Empty (stdlib only)
├── requirements-build.txt # Optional: pyinstaller for build_app.sh
├── CHANGELOG.md           # Version history
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

---

## Import / export

**File → Import from file...** loads commands and secrets from a JSON file.

Use **samples/import_sample.json** as a template. It includes sample categories (k8s, docker, git, **devstack**, **openstack**) and many ready-to-use commands (including DevStack and OpenStack CLI).

**Format:**

```json
{
  "categories": ["k8s", "docker", "devstack"],
  "commands": [
    { "title": "Get pods", "command": "kubectl get pods", "category": "k8s" },
    { "title": "DevStack stack", "command": "./stack.sh", "category": "devstack", "tags": "Production" }
  ],
  "secrets": [
    { "title": "API Key", "secret": "your-secret", "description": "Optional" }
  ]
}
```

- **categories** (optional): category names to create if missing  
- **commands**: `{ "title", "command", "category" }`; optional **"tags"** (comma-separated, e.g. `"Production, Debug"`)  
- **secrets**: `{ "title", "secret", "description" }` (description optional)

---

## Features

- **Developer Tool theme:** Slate/Zinc dark theme by default; Inter + JetBrains Mono typography. Toggle light mode in View → Dark Mode.
- **Tabs:** **Commands** | **Secrets** | **Notes** | **Todo** in one app.
- **Commands:** Categories in sidebar; **tags** (e.g. Production, Debug) as colored chips; **ghost actions** (Copy / Edit / Delete) on hover; double-click to copy. **Bulk select** with checkboxes and **Bulk Delete** / **Bulk Export**.
- **Global search:** Search bar in the header (available from any tab). **Universal search** across all categories; **recent searches** dropdown. **Fast search** with in-memory cache and capped results for responsiveness.
- **Secrets:** Masked by default; **Show** to reveal; copy with one click. Toast: **“Copied to clipboard”** instead of status bar.
- **Notes:** Two-column grid; add / edit / delete notes (title + content). **Copy** (content only, no title) and **Copy with title** (right-click menu).
- **Todo:** Daily task list; **segment filter** (All | Pending | Done); double-click to mark done; **Clear completed**.
- **Shortcuts:** Ctrl+N (add command), Ctrl+Shift+N (add category), Ctrl+F (focus search), Ctrl+Q (quit).

---

## Development

Run tests from project root (no pytest required):

```bash
python3 tests/test_db.py
```

With pytest: `python3 -m pytest tests/ -v`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to report issues, suggest features, or send patches.

---

## License

[MIT](LICENSE)

Copyright (c) 2025 CmdVault contributors
