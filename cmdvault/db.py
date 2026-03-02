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
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        );
        INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'general');
    """)
    conn.commit()
    # Migration: add tags to commands if missing
    try:
        conn.execute("ALTER TABLE commands ADD COLUMN tags TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists


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
    """Return commands as list of dicts: id, title, command, category_id, tags."""
    cols = "id, title, command, category_id"
    try:
        conn.execute("SELECT tags FROM commands LIMIT 1")
        cols = "id, title, command, category_id, tags"
    except sqlite3.OperationalError:
        pass
    if category_id is not None:
        cur = conn.execute(
            f"SELECT {cols} FROM commands WHERE category_id = ? ORDER BY title",
            (category_id,)
        )
    else:
        cur = conn.execute(f"SELECT {cols} FROM commands ORDER BY title")
    rows = cur.fetchall()
    out = []
    for row in rows:
        d = dict(row)
        if "tags" not in d:
            d["tags"] = ""
        out.append(d)
    return out


def add_command(
    conn: sqlite3.Connection,
    title: str,
    command: str,
    category_id: int,
    tags: Optional[str] = None,
) -> int:
    """Insert a command; return its id. tags: comma-separated string."""
    tags = (tags or "").strip()
    try:
        cur = conn.execute(
            "INSERT INTO commands (title, command, category_id, tags) VALUES (?, ?, ?, ?)",
            (title.strip(), command.strip(), category_id, tags)
        )
    except sqlite3.OperationalError:
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
    tags: Optional[str] = None,
) -> None:
    """Update an existing command."""
    tags = (tags or "").strip()
    try:
        conn.execute(
            "UPDATE commands SET title = ?, command = ?, category_id = ?, tags = ? WHERE id = ?",
            (title.strip(), command.strip(), category_id, tags, command_id)
        )
    except sqlite3.OperationalError:
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


# --- Notes ---

def list_notes(conn: sqlite3.Connection) -> list:
    """Return all notes as list of dicts: id, title, content, created_at."""
    cur = conn.execute(
        "SELECT id, title, content, created_at FROM notes ORDER BY id DESC"
    )
    return [dict(row) for row in cur.fetchall()]


def add_note(conn: sqlite3.Connection, title: str, content: str) -> int:
    """Insert a note; return its id."""
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    cur = conn.execute(
        "INSERT INTO notes (title, content, created_at) VALUES (?, ?, ?)",
        (title.strip(), content.strip(), now)
    )
    conn.commit()
    return cur.lastrowid


def update_note(conn: sqlite3.Connection, note_id: int, title: str, content: str) -> None:
    """Update an existing note."""
    conn.execute(
        "UPDATE notes SET title = ?, content = ? WHERE id = ?",
        (title.strip(), content.strip(), note_id)
    )
    conn.commit()


def delete_note(conn: sqlite3.Connection, note_id: int) -> None:
    """Delete a note by id."""
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()


# --- Todos (daily tasks) ---

def list_todos(conn: sqlite3.Connection) -> list:
    """Return all todos as list of dicts: id, title, done, sort_order, created_at. Pending first, then done."""
    cur = conn.execute(
        "SELECT id, title, done, sort_order, created_at FROM todos ORDER BY done ASC, sort_order ASC, id ASC"
    )
    return [dict(row) for row in cur.fetchall()]


def add_todo(conn: sqlite3.Connection, title: str) -> int:
    """Insert a todo; return its id."""
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    cur = conn.execute(
        "INSERT INTO todos (title, done, sort_order, created_at) VALUES (?, 0, 0, ?)",
        (title.strip(), now)
    )
    conn.commit()
    return cur.lastrowid


def update_todo(conn: sqlite3.Connection, todo_id: int, title: Optional[str] = None, done: Optional[int] = None) -> None:
    """Update a todo: title and/or done."""
    if title is not None and done is not None:
        conn.execute("UPDATE todos SET title = ?, done = ? WHERE id = ?", (title.strip(), done, todo_id))
    elif title is not None:
        conn.execute("UPDATE todos SET title = ? WHERE id = ?", (title.strip(), todo_id))
    elif done is not None:
        conn.execute("UPDATE todos SET done = ? WHERE id = ?", (done, todo_id))
    conn.commit()


def toggle_todo_done(conn: sqlite3.Connection, todo_id: int) -> None:
    """Flip the done flag for a todo."""
    cur = conn.execute("SELECT done FROM todos WHERE id = ?", (todo_id,))
    row = cur.fetchone()
    if row:
        new_done = 1 if row[0] == 0 else 0
        conn.execute("UPDATE todos SET done = ? WHERE id = ?", (new_done, todo_id))
        conn.commit()


def delete_todo(conn: sqlite3.Connection, todo_id: int) -> None:
    """Delete a todo by id."""
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()


def delete_completed_todos(conn: sqlite3.Connection) -> int:
    """Delete all todos where done=1. Returns number deleted."""
    cur = conn.execute("DELETE FROM todos WHERE done = 1")
    conn.commit()
    return cur.rowcount


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


def get_recent_searches(conn: sqlite3.Connection, max_count: int = 10) -> list:
    """Return list of recent search strings (newest first)."""
    val = get_setting(conn, "recent_searches")
    if not val:
        return []
    try:
        import json
        out = json.loads(val)
        return (out or [])[:max_count]
    except Exception:
        return []


def add_recent_search(conn: sqlite3.Connection, query: str) -> None:
    """Prepend query to recent searches, dedupe, keep max 10."""
    import json
    query = (query or "").strip()
    if not query:
        return
    current = get_recent_searches(conn, max_count=20)
    current = [q for q in current if q != query]
    current.insert(0, query)
    set_setting(conn, "recent_searches", json.dumps(current[:10]))
