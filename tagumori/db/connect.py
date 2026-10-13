import sqlite3
from pathlib import Path


def get_connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def open_readonly(path: Path) -> sqlite3.Connection:
    """Opens an existing db without creating or modifying anything.

    Not `immutable=1`: that ignores the WAL and loses unflushed data.
    """
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
