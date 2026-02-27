# cmdvault/db.py
"""
Database logic for CmdVault.
SQLite schema: categories, commands, settings (for dark mode and preferences).
"""

import sqlite3
import os
from typing import Optional

# Default DB path: use XDG data dir so it's writable when installed system-wide
def _db_path() -> str:
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    cmdvault_dir = os.path.join(data_home, "cmdvault")
    os.makedirs(cmdvault_dir, exist_ok=True)
    return os.path.join(cmdvault_dir, "cmdvault.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database; create file and tables if needed."""
    path = db_path or _db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # access columns by name
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist. Add secret column to commands if missing."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            command TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            secret TEXT NOT NULL,
            description TEXT
        );
        INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'general');
    """)
    conn.commit()


# --- Categories ---

def list_categories(conn: sqlite3.Connection) -> list:
    """Return all categories as list of dicts with id, name."""
    cur = conn.execute(
        "SELECT id, name FROM categories ORDER BY name"
    )
    return [dict(row) for row in cur.fetchall()]


def add_category(conn: sqlite3.Connection, name: str) -> int:
    """Insert a category; return its id. Raises on duplicate name."""
    cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name.strip(),))
    conn.commit()
    return cur.lastrowid


def delete_category(conn: sqlite3.Connection, category_id: int) -> None:
    """Delete a category. Caller should check for existing commands and warn."""
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()


def count_commands_in_category(conn: sqlite3.Connection, category_id: int) -> int:
    """Return number of commands in the given category."""
    cur = conn.execute(
        "SELECT COUNT(*) FROM commands WHERE category_id = ?",
        (category_id,)
    )
    return cur.fetchone()[0]


# --- Commands ---

def list_commands(
    conn: sqlite3.Connection,
    category_id: Optional[int] = None,
) -> list:
    """Return commands as list of dicts: id, title, command, category_id."""
    if category_id is not None:
        cur = conn.execute(
            "SELECT id, title, command, category_id FROM commands WHERE category_id = ? ORDER BY title",
            (category_id,)
        )
    else:
        cur = conn.execute(
            "SELECT id, title, command, category_id FROM commands ORDER BY title"
        )
    return [dict(row) for row in cur.fetchall()]


def add_command(
    conn: sqlite3.Connection,
    title: str,
    command: str,
    category_id: int,
) -> int:
    """Insert a command; return its id."""
    cur = conn.execute(
        "INSERT INTO commands (title, command, category_id) VALUES (?, ?, ?)",
        (title.strip(), command.strip(), category_id)
    )
    conn.commit()
    return cur.lastrowid


def update_command(
    conn: sqlite3.Connection,
    command_id: int,
    title: str,
    command: str,
    category_id: int,
) -> None:
    """Update an existing command."""
    conn.execute(
        "UPDATE commands SET title = ?, command = ?, category_id = ? WHERE id = ?",
        (title.strip(), command.strip(), category_id, command_id)
    )
    conn.commit()


def delete_command(conn: sqlite3.Connection, command_id: int) -> None:
    """Delete a command by id."""
    conn.execute("DELETE FROM commands WHERE id = ?", (command_id,))
    conn.commit()


# --- Secrets (separate from commands; permanent "Secret key" section) ---

def list_secrets(conn: sqlite3.Connection) -> list:
    """Return all secrets as list of dicts: id, title, secret, description."""
    cur = conn.execute(
        "SELECT id, title, secret, description FROM secrets ORDER BY title"
    )
    return [dict(row) for row in cur.fetchall()]


def add_secret(
    conn: sqlite3.Connection,
    title: str,
    secret: str,
    description: Optional[str] = None,
) -> int:
    """Insert a secret; return its id."""
    desc = (description or "").strip() or None
    cur = conn.execute(
        "INSERT INTO secrets (title, secret, description) VALUES (?, ?, ?)",
        (title.strip(), secret.strip(), desc)
    )
    conn.commit()
    return cur.lastrowid


def update_secret(
    conn: sqlite3.Connection,
    secret_id: int,
    title: str,
    secret: str,
    description: Optional[str] = None,
) -> None:
    """Update an existing secret."""
    desc = (description or "").strip() or None
    conn.execute(
        "UPDATE secrets SET title = ?, secret = ?, description = ? WHERE id = ?",
        (title.strip(), secret.strip(), desc, secret_id)
    )
    conn.commit()


def delete_secret(conn: sqlite3.Connection, secret_id: int) -> None:
    """Delete a secret by id."""
    conn.execute("DELETE FROM secrets WHERE id = ?", (secret_id,))
    conn.commit()


# --- Settings (e.g. dark mode) ---

def get_setting(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """Return value for key, or None."""
    cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set a key-value in settings."""
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
