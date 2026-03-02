"""Basic tests for CmdVault db module (no GUI)."""
import os
import tempfile
import sys

# Allow importing cmdvault from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cmdvault.db as db


def test_connection_and_schema():
    """get_connection creates DB and tables; list_categories returns at least 'general'."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.db")
        conn = db.get_connection(path)
        try:
            cats = db.list_categories(conn)
            assert isinstance(cats, list)
            names = [c["name"] for c in cats]
            assert "general" in names
        finally:
            conn.close()


def test_add_and_list_command():
    """add_command and list_commands work with tags."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.db")
        conn = db.get_connection(path)
        try:
            cid = db.add_command(conn, "Test", "echo 1", 1, tags="dev")
            assert cid > 0
            rows = db.list_commands(conn, category_id=1)
            assert any(r["title"] == "Test" and (r.get("tags") or "") == "dev" for r in rows)
        finally:
            conn.close()


if __name__ == "__main__":
    test_connection_and_schema()
    test_add_and_list_command()
    print("All tests passed.")
