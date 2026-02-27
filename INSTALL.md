# Install CmdVault and open from app menu

## Steps

1. **Open a terminal** and go to the project folder (after cloning the repo):
   ```bash
   cd path/to/cmdvault
   ```

2. **Run the installer** (no `sudo` needed; installs under `~/.local`):
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Open CmdVault**
   - **From app menu:** Open your applications menu (e.g. Activities → Applications), search for **CmdVault**, and click it. It is under **Utility** or **Development**.
   - **From terminal:** Run:
     ```bash
     ~/.local/bin/cmdvault
     ```
     To use the short name `cmdvault` from anywhere, add this to your `~/.bashrc` once:
     ```bash
     export PATH="$HOME/.local/bin:$PATH"
     ```
     Then run `source ~/.bashrc` or open a new terminal and type `cmdvault`.

4. **If CmdVault does not appear in the app menu**
   - Log out and log back in (or reboot).
   - Or run:
     ```bash
     update-desktop-database ~/.local/share/applications
     ```
     Then check the menu again.

Data (commands and secrets) is stored in `~/.local/share/cmdvault/cmdvault.db`.
