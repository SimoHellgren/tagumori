import sqlite3
from contextlib import closing
from pathlib import Path

from .connect import get_connection, open_readonly
from .migrations import LATEST_VERSION, migrate

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Present in every schema version; what makes a file recognisable as a vault.
CORE_TABLES = {"file", "tag", "file_tag"}


def init_db(path: Path) -> None:
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        migrate(conn)


def is_tagumori_db(path: Path) -> bool:
    """Whether `path` looks like a tagumori vault this version can adopt.

    Needs tagumori's core tables and a schema version that is set (0 means no
    schema was ever applied) and not newer than this version knows about.
    """
    try:
        with closing(open_readonly(path)) as conn:
            (version,) = conn.execute("PRAGMA user_version").fetchone()
            tables = {
                name
                for (name,) in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
    except sqlite3.DatabaseError:  # includes "file is not a database"
        return False

    return 0 < version <= LATEST_VERSION and CORE_TABLES <= tables
