import sqlite3
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from tagumori import crud
from tagumori.db.init import SCHEMA_PATH
from tagumori.db.migrations import migrate
from tagumori.models import Tag


@pytest.fixture
def conn() -> Generator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def make_file(tmp_path: Path) -> Callable[..., Path]:
    """Creates a real (empty) file on disk under tmp_path."""

    def _make(name: str = "file.txt") -> Path:
        f = tmp_path / name
        f.write_text("")
        return f

    return _make


@pytest.fixture
def make_tag(conn: sqlite3.Connection) -> Callable[..., Tag]:
    def _make(name: str = "rock", category: str | None = None) -> Tag:
        return crud.tag.create(conn, name, category)

    return _make


@pytest.fixture
def make_tagged_file(conn: sqlite3.Connection) -> Callable[..., int]:
    """Creates a file (not necessarily present on disk) and attaches tag trees.

    tag_paths is a list of tuples, e.g. [("genre", "rock"), ("mood",)].
    Each tuple is a root -> child -> grandchild chain. Returns the file id.
    """

    def _make(path_str: str, tag_paths: list[tuple[str, ...]]) -> int:
        file_row = crud.file.get_or_create(conn, Path(path_str))
        for tag_path in tag_paths:
            parent_id = None
            for tag_name in tag_path:
                tag = crud.tag.get_or_create(conn, tag_name)
                parent_id = crud.file_tag.attach(conn, file_row.id, tag.id, parent_id)
        return file_row.id

    return _make
