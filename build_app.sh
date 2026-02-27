#!/bin/bash
# Build a standalone CmdVault executable with PyInstaller.
# Run from the CMDVault project root. Output: dist/CmdVault

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Install with: pip install --user pyinstaller"
    exit 1
fi

pyinstaller cmdvault_app.spec

echo ""
echo "Done. Run the app with: ./dist/CmdVault"
echo "Or copy dist/CmdVault to anywhere (e.g. ~/bin) and run it."
