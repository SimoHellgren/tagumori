import sqlite3
from collections.abc import Generator

import pytest

from tagumori.db.init import SCHEMA_PATH
from tagumori.db.migrations import migrate


@pytest.fixture
def conn() -> Generator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    migrate(conn)
    yield conn
    conn.close()
