import sqlite3
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from tagumori.db.init import SCHEMA_PATH
from tagumori.db.migrations import migrate
from tagumori.models import Tag
from tagumori.vault import Vault


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
def vault(conn: sqlite3.Connection) -> Vault:
    return Vault(conn)


@pytest.fixture
def make_file(tmp_path: Path) -> Callable[..., Path]:
    """Creates a real (empty) file on disk under tmp_path."""

    def _make(name: str = "file.txt") -> Path:
        f = tmp_path / name
        f.write_text("")
        return f

    return _make


@pytest.fixture
def make_tag(vault: Vault) -> Callable[..., Tag]:
    def _make(name: str = "rock", category: str | None = None) -> Tag:
        return vault.tags.create(name, category)

    return _make


@pytest.fixture
def make_tagged_file(vault: Vault) -> Callable[..., int]:
    """Creates a file (not necessarily present on disk) and attaches tag trees.

    tag_paths is a list of tuples, e.g. [("genre", "rock"), ("mood",)].
    Each tuple is a root -> child -> grandchild chain. Returns the file id.
    """

    def _make(path_str: str, tag_paths: list[tuple[str, ...]]) -> int:
        file_row = vault.files.get_or_create(Path(path_str))
        for tag_path in tag_paths:
            parent_id = None
            for tag_name in tag_path:
                tag = vault.tags.get_or_create(tag_name)
                parent_id = vault.file_tags.attach(file_row.id, tag.id, parent_id)
        return file_row.id

    return _make
