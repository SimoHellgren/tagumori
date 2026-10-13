import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tagumori.db.backup import snapshot
from tagumori.db.connect import get_connection, open_readonly
from tagumori.db.init import SCHEMA_PATH, init_db, is_tagumori_db
from tagumori.db.migrations import LATEST_VERSION


def count_tags(path: Path) -> int:
    with closing(open_readonly(path)) as conn:
        return conn.execute("SELECT COUNT(*) FROM tag").fetchone()[0]


@pytest.fixture
def vault_file(tmp_path: Path) -> Path:
    """A real, initialised vault db with one tag in it."""
    path = tmp_path / "vault.db"
    init_db(path)
    with closing(get_connection(path)) as conn, conn:
        conn.execute("INSERT INTO tag (name) VALUES ('rock')")
    return path


def make_db(path: Path, *statements: str) -> Path:
    """A plain SQLite file with exactly the given statements run in it."""
    with closing(sqlite3.connect(path)) as conn, conn:
        for statement in statements:
            conn.execute(statement)
    return path


class TestOpenReadonly:
    def test_cannot_write(self, vault_file):
        with closing(open_readonly(vault_file)) as conn:
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                conn.execute("INSERT INTO tag (name) VALUES ('jazz')")

    def test_does_not_create_missing_file(self, tmp_path):
        missing = tmp_path / "missing.db"

        with pytest.raises(sqlite3.OperationalError):
            open_readonly(missing)

        assert not missing.exists()

    def test_accepts_relative_path(self, vault_file, monkeypatch):
        monkeypatch.chdir(vault_file.parent)

        assert count_tags(Path(vault_file.name)) == 1

    def test_sees_data_a_live_writer_has_not_checkpointed(self, tmp_path):
        """Data may sit in the -wal file while the writer is still open."""
        path = tmp_path / "live.db"
        init_db(path)
        writer = get_connection(path)
        try:
            with writer:
                writer.execute("INSERT INTO tag (name) VALUES ('rock')")

            assert Path(f"{path}-wal").exists()
            assert count_tags(path) == 1
        finally:
            writer.close()


class TestIsTagumoriDb:
    def test_real_vault(self, vault_file):
        assert is_tagumori_db(vault_file)

    def test_relative_path(self, vault_file, monkeypatch):
        monkeypatch.chdir(vault_file.parent)

        assert is_tagumori_db(Path(vault_file.name))

    def test_vault_with_a_live_writer(self, vault_file):
        writer = get_connection(vault_file)
        try:
            with writer:
                writer.execute("INSERT INTO tag (name) VALUES ('jazz')")

            assert is_tagumori_db(vault_file)
        finally:
            writer.close()

    def test_missing_file_is_false_and_not_created(self, tmp_path):
        missing = tmp_path / "missing.db"

        assert not is_tagumori_db(missing)
        assert not missing.exists()

    def test_text_file(self, tmp_path):
        path = tmp_path / "notes.txt"
        path.write_text("hello")

        assert not is_tagumori_db(path)

    def test_empty_sqlite_file(self, tmp_path):
        assert not is_tagumori_db(make_db(tmp_path / "empty.db"))

    def test_unrelated_sqlite_db(self, tmp_path):
        other = make_db(
            tmp_path / "other.db",
            "CREATE TABLE contacts (name TEXT)",
            "PRAGMA user_version = 2",
        )

        assert not is_tagumori_db(other)

    def test_schema_applied_but_version_never_set(self, tmp_path):
        """Right tables, but user_version 0: not something tagumori produced."""
        path = tmp_path / "v0.db"
        with closing(sqlite3.connect(path)) as conn:
            conn.executescript(SCHEMA_PATH.read_text())
            conn.execute("PRAGMA user_version = 0")

        assert not is_tagumori_db(path)

    def test_newer_than_this_version(self, vault_file):
        with closing(sqlite3.connect(vault_file)) as conn:
            conn.execute(f"PRAGMA user_version = {LATEST_VERSION + 1}")

        assert not is_tagumori_db(vault_file)

    @pytest.mark.parametrize("table", ["file", "tag", "file_tag"])
    def test_missing_a_core_table(self, vault_file, table):
        with closing(sqlite3.connect(vault_file)) as conn, conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(f"DROP TABLE {table}")

        assert not is_tagumori_db(vault_file)

    def test_older_supported_version(self, tmp_path):
        """A db from before the latest migrations is still adoptable."""
        path = tmp_path / "old.db"
        with closing(sqlite3.connect(path)) as conn:
            conn.executescript(SCHEMA_PATH.read_text())  # leaves user_version = 2

        assert is_tagumori_db(path)


class TestSnapshot:
    def test_copies_the_data(self, vault_file, tmp_path):
        dest = tmp_path / "copy.db"

        with closing(open_readonly(vault_file)) as source:
            snapshot(source, dest)

        assert is_tagumori_db(dest)
        assert count_tags(dest) == 1

    def test_leaves_the_source_alone(self, vault_file, tmp_path):
        dest = tmp_path / "copy.db"
        before = count_tags(vault_file)

        with closing(open_readonly(vault_file)) as source:
            snapshot(source, dest)

        assert vault_file.exists()
        assert count_tags(vault_file) == before

    def test_copy_is_independent_of_the_source(self, vault_file, tmp_path):
        dest = tmp_path / "copy.db"
        with closing(open_readonly(vault_file)) as source:
            snapshot(source, dest)

        with closing(get_connection(vault_file)) as conn, conn:
            conn.execute("INSERT INTO tag (name) VALUES ('jazz')")

        assert count_tags(vault_file) == 2
        assert count_tags(dest) == 1

    def test_includes_data_a_live_writer_has_not_checkpointed(self, tmp_path):
        """What copying only the .db file would lose."""
        path = tmp_path / "live.db"
        init_db(path)
        writer = get_connection(path)
        try:
            with writer:
                writer.execute("INSERT INTO tag (name) VALUES ('rock')")
            dest = tmp_path / "copy.db"

            with closing(open_readonly(path)) as source:
                snapshot(source, dest)

            assert count_tags(dest) == 1
        finally:
            writer.close()
