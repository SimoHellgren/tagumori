from pathlib import Path

from .connect import get_vault

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_db(path: Path):
    with get_vault(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
