# cmdvault/main.py
"""CmdVault application entry point."""

import tkinter as tk
from . import db
from .ui import CmdVaultUI


def main() -> None:
    root = tk.Tk()
    conn = db.get_connection()
    try:
        CmdVaultUI(root, conn)
        root.mainloop()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
