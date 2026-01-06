import sqlite3
from pathlib import Path

DEFAULT_VAULT_PATH = Path("vault.db")


def get_vault(path: Path = DEFAULT_VAULT_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
