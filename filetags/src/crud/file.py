from pathlib import Path
from sqlite3 import Connection


def get_by_name(conn: Connection, file: Path):
    return conn.execute("SELECT * FROM file WHERE path = ?", (file,)).fetchone()


def get_many(conn: Connection, ids: list[int]) -> list:
    phs = ",".join("?" for _ in ids)
    return conn.execute(
        f"SELECT * FROM file WHERE id in ({phs}) ORDER BY path", ids
    ).fetchall()


def get_or_create_file(conn: Connection, file: Path) -> int:
    q = """
            INSERT INTO file (path) VALUES (?)
            ON CONFLICT(path) DO UPDATE SET path=path --no-op update
            RETURNING id
        """
    (file_id,) = conn.execute(q, (str(file),)).fetchone()

    return file_id


def get_all(conn: Connection):
    return conn.execute("SELECT * FROM file ORDER BY path").fetchall()


def delete(conn: Connection, file_id: int):
    conn.execute("DELETE FROM file WHERE id = ?", (file_id,))
