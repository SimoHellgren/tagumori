from pathlib import Path

from .connect import get_connection
from .migrations import migrate

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_db(path: Path):
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        migrate(conn)
