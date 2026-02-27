# CmdVault

**A desktop app to store, search, and copy terminal commands.** Organize commands by category, fuzzy-search, and paste into your terminal with one click or double-click.

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
git clone https://github.com/YOUR_USERNAME/cmdvault.git
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

See [INSTALL.md](INSTALL.md) for more detail and troubleshooting.

### Option B — RPM (system-wide)

For Fedora, build and install an RPM:

```bash
cp -r cmdvault cmdvault-1.0
tar czvf cmdvault-1.0.tar.gz --exclude=__pycache__ --exclude=*.pyc cmdvault-1.0
sudo dnf install rpm-build
rpmbuild -ta cmdvault-1.0.tar.gz
sudo dnf install ~/rpmbuild/RPMS/noarch/cmdvault-1.0-1.fc*.noarch.rpm
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
│   ├── __main__.py       # Entry for python3 -m cmdvault & PyInstaller
│   ├── main.py            # App entry, Tk window
│   ├── ui.py              # UI (sidebar, cards, search, dialogs)
│   ├── db.py              # SQLite (categories, commands, secrets, settings)
│   ├── themes.py          # Light/dark theme
│   └── utils.py           # Clipboard, fuzzy search
├── packaging/
│   └── cmdvault.desktop   # Desktop entry for app menu
├── run_cmdvault.py        # Convenience launcher
├── install.sh             # Install to ~/.local
├── build_app.sh           # Build standalone binary (PyInstaller)
├── cmdvault.spec          # RPM spec (Fedora)
├── cmdvault_app.spec      # PyInstaller spec
├── import_sample.json     # Example for File → Import
├── requirements.txt      # Empty (stdlib only)
├── requirements-build.txt # Optional: pyinstaller for build_app.sh
├── README.md
├── INSTALL.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

---

## Import / export

**File → Import from file...** loads commands and secrets from a JSON file.

Use `import_sample.json` as a template:

```json
{
  "categories": ["k8s", "docker"],
  "commands": [
    { "title": "Get pods", "command": "kubectl get pods", "category": "k8s" }
  ],
  "secrets": [
    { "title": "API Key", "secret": "your-secret", "description": "Optional" }
  ]
}
```

- **categories** (optional): category names to create if missing  
- **commands**: `{ "title", "command", "category" }`; category is created if needed  
- **secrets**: `{ "title", "secret", "description" }` (description optional)

---

## Features

- **Categories** in the left sidebar (add / delete with confirmation)
- **Commands:** title, command, category; cards with Copy, Edit, Delete
- **Double-click** a row to copy the command to the clipboard
- **Copy** via button, right-click menu, **Ctrl+C**, or **Enter** when a row is selected
- **Fuzzy search** on title and command (live)
- **Secrets** tab for API keys and other secrets (masked, one-click copy)
- **Dark mode:** View → Dark Mode (saved)
- **Shortcuts:** Ctrl+N (add command), Ctrl+Shift+N (add category), Ctrl+F (focus search), Ctrl+Q (quit)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to report issues, suggest features, or send patches.

---

## Before pushing to GitHub

- Replace **YOUR_USERNAME** in this README and in [CONTRIBUTING.md](CONTRIBUTING.md) with your GitHub username (in clone URLs and issue links).
- Ensure the repo name matches the URLs (e.g. `cmdvault` → `https://github.com/YOUR_USERNAME/cmdvault`).

## License

[MIT](LICENSE)
