#!/bin/bash
# Install CmdVault as a Fedora desktop application (no RPM).
# Run from the CMDVault project directory. Uses ~/.local for user install.
set -e
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/.local}"
BIN_DIR="$INSTALL_ROOT/bin"
APP_DIR="$INSTALL_ROOT/lib/cmdvault"
APPS_DIR="$INSTALL_ROOT/share/applications"
mkdir -p "$BIN_DIR" "$APP_DIR" "$APPS_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR/cmdvault/"*.py "$APP_DIR/"
# Launcher must set PYTHONPATH so "python3 -m cmdvault.main" finds the installed package
LIB_DIR="$(dirname "$APP_DIR")"
cat > "$BIN_DIR/cmdvault" << LAUNCHER
#!/bin/bash
export PYTHONPATH="${LIB_DIR}:\${PYTHONPATH:-}"
exec python3 -m cmdvault.main "\$@"
LAUNCHER
chmod 755 "$BIN_DIR/cmdvault"
sed 's|^Exec=cmdvault|Exec='"$BIN_DIR"'/cmdvault|' "$SCRIPT_DIR/packaging/cmdvault.desktop" > "$APPS_DIR/cmdvault.desktop"
if command -v update-desktop-database &>/dev/null; then update-desktop-database "$APPS_DIR" 2>/dev/null || true; fi
echo ""
echo "Installed to $INSTALL_ROOT"
echo "  Run from terminal: $BIN_DIR/cmdvault"
echo "  App menu: open 'CmdVault' from your applications (Utility/Development)."
echo "  If it does not appear, log out and back in once."
