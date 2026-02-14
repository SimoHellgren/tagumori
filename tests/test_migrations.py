import sqlite3

import pytest

from tagumori.db.init import SCHEMA_PATH
from tagumori.db.migrations import LATEST_VERSION, migrate


@pytest.fixture
def fresh_conn():
    """A connection with the full schema applied (simulates a new vault)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


@pytest.fixture
def v2_conn():
    """A connection at schema version 2, before migrations."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    # Ensure we're at version 2 (what schema.sql sets)
    conn.execute("PRAGMA user_version = 2")
    return conn


class TestMigrate:
    def test_migrate_from_v2_adds_ignore_tag_case(self, v2_conn):
        migrate(v2_conn)

        # Column should exist and be usable
        v2_conn.execute(
            "INSERT INTO query(name, select_tags, exclude_tags, ignore_tag_case, "
            "pattern, ignore_case, invert_match) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test", "[]", "[]", True, ".*", False, False),
        )
        row = v2_conn.execute("SELECT ignore_tag_case FROM query WHERE name = 'test'").fetchone()
        assert row["ignore_tag_case"] == 1

    def test_migrate_sets_latest_version(self, v2_conn):
        migrate(v2_conn)

        (version,) = v2_conn.execute("PRAGMA user_version").fetchone()
        assert version == LATEST_VERSION

    def test_migrate_idempotent(self, v2_conn):
        migrate(v2_conn)
        migrate(v2_conn)

        (version,) = v2_conn.execute("PRAGMA user_version").fetchone()
        assert version == LATEST_VERSION

    def test_migrate_noop_when_already_at_latest(self, fresh_conn):
        """Running migrate on a fresh DB (already at or above latest) should not fail."""
        fresh_conn.execute(f"PRAGMA user_version = {LATEST_VERSION}")
        migrate(fresh_conn)

        (version,) = fresh_conn.execute("PRAGMA user_version").fetchone()
        assert version == LATEST_VERSION

    def test_migrate_preserves_existing_data(self, v2_conn):
        """Existing query rows should survive the migration."""
        v2_conn.execute(
            "INSERT INTO query(name, select_tags, exclude_tags, pattern, "
            "ignore_case, invert_match) VALUES (?, ?, ?, ?, ?, ?)",
            ("existing", "[]", "[]", ".*", False, False),
        )

        migrate(v2_conn)

        row = v2_conn.execute("SELECT * FROM query WHERE name = 'existing'").fetchone()
        assert row is not None
        assert row["ignore_tag_case"] is None or row["ignore_tag_case"] == 0
