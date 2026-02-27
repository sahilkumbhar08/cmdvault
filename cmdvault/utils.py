# cmdvault/utils.py
"""
Clipboard and fuzzy search helpers.
Uses Tkinter clipboard and difflib for fuzzy matching.
"""

import difflib
from typing import List


def copy_to_clipboard(root, text: str) -> None:
    """Copy text to system clipboard using Tkinter."""
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update_idletasks()


def fuzzy_match(query: str, target: str) -> bool:
    """Simple fuzzy match: query characters appear in target in order. Case-insensitive."""
    if not query.strip():
        return True
    q = query.lower().strip()
    t = target.lower()
    idx = 0
    for c in q:
        pos = t.find(c, idx)
        if pos == -1:
            return False
        idx = pos + 1
    return True


def fuzzy_score(query: str, target: str) -> float:
    """Return a similarity score in [0, 1] for ordering results."""
    if not query.strip():
        return 1.0
    return difflib.SequenceMatcher(None, query.lower(), target.lower()).ratio()


def filter_commands_fuzzy(
    commands: List[dict],
    query: str,
    *,
    search_title: bool = True,
    search_command: bool = True,
) -> List[dict]:
    """Filter commands by fuzzy matching on title and/or command. Returns list sorted by relevance."""
    if not query.strip():
        return list(commands)
    q = query.strip().lower()
    scored = []
    for cmd in commands:
        title = (cmd.get("title") or "").lower()
        command = (cmd.get("command") or "").lower()
        if search_title and fuzzy_match(q, title):
            score = fuzzy_score(q, title)
            scored.append((score, cmd))
            continue
        if search_command and fuzzy_match(q, command):
            score = fuzzy_score(q, command)
            scored.append((score, cmd))
    scored.sort(key=lambda x: -x[0])
    return [cmd for _, cmd in scored]
