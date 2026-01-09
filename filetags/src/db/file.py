from pathlib import Path
from sqlite3 import Connection


def get_or_create_file(conn: Connection, file: Path) -> int:
    q = """
            INSERT INTO file (path) VALUES (?)
            ON CONFLICT(path) DO UPDATE SET path=path --no-op update
            RETURNING id
        """
    (file_id,) = conn.execute(q, (str(file),)).fetchone()

    return file_id
