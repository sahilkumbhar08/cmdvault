# cmdvault/utils.py
"""
Clipboard and fast search helpers.
Optimized for responsive search: fast substring + in-order match, no difflib.
"""

from typing import List


def copy_to_clipboard(root, text: str) -> None:
    """Copy text to system clipboard using Tkinter."""
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update_idletasks()


def _fuzzy_match(q: str, target: str) -> bool:
    """Query chars appear in target in order. Case-insensitive. Fast."""
    if not q:
        return True
    t = target.lower()
    idx = 0
    for c in q:
        pos = t.find(c, idx)
        if pos == -1:
            return False
        idx = pos + 1
    return True


def _fast_score(q: str, target: str) -> float:
    """Fast relevance: substring > startswith > in-order. No SequenceMatcher."""
    if not q:
        return 1.0
    t = target.lower()
    if q in t:
        return 1.0 - (t.find(q) * 0.001)  # prefer earlier match
    if t.startswith(q):
        return 0.95
    if not _fuzzy_match(q, t):
        return 0.0
    # In-order match: prefer shorter span and earlier start
    idx, span = 0, 0
    start = -1
    for c in q:
        pos = t.find(c, idx)
        if pos == -1:
            return 0.0
        if start < 0:
            start = pos
        span += pos - idx
        idx = pos + 1
    return max(0.1, 0.9 - span * 0.01 - start * 0.001)


def filter_commands_fuzzy(
    commands: List[dict],
    query: str,
    *,
    search_title: bool = True,
    search_command: bool = True,
) -> List[dict]:
    """Filter by fast substring/fuzzy match. Returns list sorted by relevance. Kept name for API."""
    if not query.strip():
        return list(commands)
    q = query.strip().lower()
    scored = []
    for cmd in commands:
        title = (cmd.get("title") or "").lower()
        command = (cmd.get("command") or "").lower()
        best = 0.0
        if search_title and _fuzzy_match(q, title):
            best = max(best, _fast_score(q, title))
        if search_command and _fuzzy_match(q, command):
            best = max(best, _fast_score(q, command))
        if best > 0:
            scored.append((best, cmd))
    scored.sort(key=lambda x: -x[0])
    return [cmd for _, cmd in scored]
