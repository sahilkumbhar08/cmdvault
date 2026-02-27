# Contributing to CmdVault

Thanks for your interest in contributing.

## How to contribute

- **Bug reports and feature ideas:** Open an [Issue](https://github.com/YOUR_USERNAME/cmdvault/issues).
- **Code changes:** Open a Pull Request from a fork. Keep changes focused and add a short description.

## Development setup

1. Clone the repo and run from source:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cmdvault.git
   cd cmdvault
   python3 -m cmdvault.main
   ```
2. No virtualenv or `pip install` is required; the app uses only the Python standard library (tkinter, sqlite3).
3. Data and settings live in `~/.local/share/cmdvault/` (XDG). Delete that folder to reset.

## Code style

- Python 3.9+.
- Prefer clear names and short functions. No formal style guide; match the existing code.

## Testing

- Manual testing only (GUI + SQLite). Run the app, add/edit/delete categories and commands, try search and import.

## License

By contributing, you agree that your contributions will be licensed under the project’s [MIT License](LICENSE).
